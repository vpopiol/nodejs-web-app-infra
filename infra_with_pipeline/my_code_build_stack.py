from aws_cdk import (
    # Duration,
    Stack,
    aws_iam as iam,
    # aws_sqs as sqs,
)
from aws_cdk.aws_codebuild import BuildEnvironment, BuildEnvironmentVariable, BuildImageConfig, LinuxBuildImage, PipelineProject
from constructs import Construct
from aws_cdk.aws_codecommit import Repository
from aws_cdk.aws_codepipeline import Pipeline, StageProps, Artifact
from aws_cdk.aws_codepipeline_actions import CodeCommitSourceAction, CodeBuildAction

class MyCodeBuildStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        x86_build_environment = BuildEnvironment(
            build_image=LinuxBuildImage.AMAZON_LINUX_2_3,
            privileged=True,
            environment_variables={
                'AWS_DEFAULT_REGION': BuildEnvironmentVariable(value='us-east-1'),
                'AWS_ACCOUNT_ID':     BuildEnvironmentVariable(value='376611517776'),
                'IMAGE_REPO_NAME':    BuildEnvironmentVariable(value='node-web-app'),
                'IMAGE_TAG':          BuildEnvironmentVariable(value='latest-amd64')
            }
        )
        build_project = PipelineProject(self, 'BuildProjectX86', environment=x86_build_environment)
        build_project.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryPowerUser'))
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
                            project=build_project,
                        )
                    ]
                )
            ]
        )

        