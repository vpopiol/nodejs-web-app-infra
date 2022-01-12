import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    # Duration,
    Stack,
    Stage,
    # aws_sqs as sqs,
)
from infra_with_pipeline.nodejs_webapp_pipeline_stack import NodeJsWebappPipelineStack
from infra_with_pipeline.infra_vpc_stack import InfraVpcStack
from infra_with_pipeline.infra_ec2_stack import InfraEc2Stack
from infra_with_pipeline.infra_ecs_stack import InfraEcsStack

class NodeJsWebappPipelineStge(Stage):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        code_build_stack = NodeJsWebappPipelineStack(self, 'CodeBuildStack')
        infra_vpc_stack = InfraVpcStack(self, 'InfraVpcStack')
        infra_ec2_stack = InfraEc2Stack(self, 'InfraEc2Stack', 
            vpc=infra_vpc_stack.vpc,
            alb_http_listener=infra_vpc_stack.alb_http_listener,
            ecr_repo=code_build_stack.ecr_repo
        )
        infra_ecs_stack = InfraEcsStack(self, 'InfraEcsStack', 
            vpc=infra_vpc_stack.vpc,
            alb_http_listener=infra_vpc_stack.alb_http_listener,
            ecr_repo=code_build_stack.ecr_repo
        )
        # infra_stack = InfraStack(self, 'InfraStack', ecr_repo=code_build_stack.ecr_repo)

