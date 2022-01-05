from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
)
from aws_cdk.aws_codebuild import PipelineProject
from constructs import Construct
from aws_cdk.aws_codecommit import Repository
from aws_cdk.aws_codepipeline import Pipeline, StageProps, Artifact
from aws_cdk.aws_codepipeline_actions import CodeCommitSourceAction, CodeBuildAction

class MyCodeBuildStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        source_output = Artifact(artifact_name='source')
        pipeline = Pipeline(
            self, "Pipeline",
            pipeline_name="nodejs-web-app2",
            stages=[
                StageProps(
                    stage_name='Source',
                    actions=[
                        CodeCommitSourceAction(
                            action_name='CodeCommit',
                            repository=Repository.from_repository_name(self, 'repo', 'nodejs-web-app'),
                            output=source_output
                        )
                    ]
                ),
                StageProps(
                    stage_name='Build',
                    actions=[
                        CodeBuildAction(
                            action_name='DockerBuildImages',
                            input=source_output,
                            project=PipelineProject(self, 'BuildProjectX86'

                            )
                        )
                    ]
                )
            ]
        )

        