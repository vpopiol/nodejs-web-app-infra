from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
)
from constructs import Construct
from aws_cdk.pipelines import CodePipeline, CodePipelineSource, ShellStep
from aws_cdk.aws_codecommit import Repository

class MyPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        pipeline = CodePipeline(
            self, "Pipeline",
            pipeline_name="MyPipeline",
            synth=ShellStep("Synth",
                input=CodePipelineSource.code_commit(Repository.from_repository_name(self, 'MyRepo', 'nodejs-web-app-with-infra'), branch='master'),
                commands=[
                    "npm install -g aws-cdk", 
                    "python -m pip install -r requirements.txt", 
                    "cdk synth"
                ]
            )
        )