import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    # Duration,
    Stack,
    Stage,
    # aws_sqs as sqs,
)
from infra_with_pipeline.nodejs_webapp_pipeline_stack import NodeJsWebappPipelineStack

class NodeJsWebappPipelineStge(Stage):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        code_build_stack = NodeJsWebappPipelineStack(self, 'CodeBuildStack')

