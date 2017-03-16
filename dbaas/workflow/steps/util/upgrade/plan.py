# -*- coding: utf-8 -*-
from util import build_context_script, exec_remote_command
from dbaas_cloudstack.models import HostAttr, PlanAttr
from dbaas_nfsaas.models import HostAttr as HostAttrNfsaas
from workflow.steps.util.base import BaseInstanceStep


class PlanStep(BaseInstanceStep):

    def __init__(self, instance):
        super(PlanStep, self).__init__(instance)

        self.host = self.instance.hostname
        self.host_cs = HostAttr.objects.get(host=self.host)

        try:
            self.host_nfs = HostAttrNfsaas.objects.get(host=self.host)
        except HostAttrNfsaas.DoesNotExist:
            self.host_nfs = None

        self.database = self.instance.databaseinfra.databases.first()

        self.plan = self.instance.databaseinfra.plan.engine_equivalent_plan
        if self.plan:
            self.cs_plan = PlanAttr.objects.get(plan=self.plan)

    @property
    def script_variables(self):
        variables = {
            'DATABASENAME': self.database.name,
            'DBPASSWORD': self.instance.databaseinfra.password,
            'HOST': self.host.hostname.split('.')[0],
            'ENGINE': self.plan.engine.engine_type.name,
            'UPGRADE': True,
            'IS_HA': self.plan.is_ha
        }

        if self.host_nfs:
            variables.update(
                {'EXPORTPATH': self.host_nfs.nfsaas_path}
            )

        variables.update(self.get_variables_specifics())
        return variables

    def get_variables_specifics(self):
        return {}

    def do(self):
        raise NotImplementedError

    def undo(self):
        pass


class Initialization(PlanStep):

    def __unicode__(self):
        return "Executing plan initial script..."

    def do(self):
        script = build_context_script(
            self.script_variables, self.cs_plan.initialization_script
        )

        output = {}
        return_code = exec_remote_command(
            self.host.address, self.host_cs.vm_user, self.host_cs.vm_password,
            script, output
        )

        if return_code != 0:
            raise EnvironmentError(
                'Could not execute initial script {}: {}'.format(
                    return_code, output
                )
            )


class Configure(PlanStep):

    def __unicode__(self):
        return "Executing plan configure script..."

    def do(self):
        script = build_context_script(
            self.script_variables, self.cs_plan.configuration_script
        )

        output = {}
        return_code = exec_remote_command(
            self.host.address, self.host_cs.vm_user, self.host_cs.vm_password,
            script, output
        )

        if return_code != 0:
            raise EnvironmentError(
                'Could not execute configure script {}: {}'.format(
                    return_code, output
                )
            )


class InitializationNewInstance(Initialization):
    def __init__(self, instance):
        super(InitializationNewInstance, self).__init__(instance)
        self.plan = self.instance.databaseinfra.plan
        self.cs_plan = PlanAttr.objects.get(plan=self.plan)


class ConfigureNewInstance(Configure):
    def __init__(self, instance):
        super(ConfigureNewInstance, self).__init__(instance)
        self.plan = self.instance.databaseinfra.plan
        self.cs_plan = PlanAttr.objects.get(plan=self.plan)
