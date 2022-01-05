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
        region = 'us-east-1'
        account = '376611517776'
        repo_name = 'node-web-app'

        # build_project_details = [
        #     {
        #         'id': 'BuildProjectX86',
        #         'action_name': 
        #         'build_image': LinuxBuildImage.AMAZON_LINUX_2_3,
        #         'image_tag': 'latest-amd64'
        #     },
        #     {
        #         'id': 'BuildProjectArm',
        #         'build_image': LinuxBuildImage.AMAZON_LINUX_2_ARM_2,
        #         'image_tag': 'latest-amd64'
        #     },
        #     {
        #         'id': 'BuildProjectManifest',
        #         'build_image': LinuxBuildImage.AMAZON_LINUX_2_3,
        #         'image_tag': 'latest'
        #     }
        # ]

        build_x86_project = self.build_project(
            project_id='BuildProjectX86',
            build_image=LinuxBuildImage.AMAZON_LINUX_2_3,
            region=region,
            account=account,
            repo_name=repo_name,
            image_tag='latest-amd64'
        )
        build_arm_project = self.build_project(
            project_id='BuildProjectArm',
            build_image=LinuxBuildImage.AMAZON_LINUX_2_ARM_2,
            region=region,
            account=account,
            repo_name=repo_name,
            image_tag='latest-arm'
        )
        build_manifest_project = self.build_project(
            project_id='BuildProjectManifest',
            build_image=LinuxBuildImage.AMAZON_LINUX_2_ARM_2,
            region=region,
            account=account,
            repo_name=repo_name,
            image_tag='latest'
        )

        # x86_build_environment = BuildEnvironment(
        #     build_image=LinuxBuildImage.AMAZON_LINUX_2_3,
        #     privileged=True,
        #     environment_variables={
        #         'AWS_DEFAULT_REGION': BuildEnvironmentVariable(value='us-east-1'),
        #         'AWS_ACCOUNT_ID':     BuildEnvironmentVariable(value='376611517776'),
        #         'IMAGE_REPO_NAME':    BuildEnvironmentVariable(value='node-web-app'),
        #         'IMAGE_TAG':          BuildEnvironmentVariable(value='latest-amd64')
        #     }
        # )
        # build_project = PipelineProject(self, 'BuildProjectX86', environment=x86_build_environment)
        # build_project.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryPowerUser'))
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
                            action_name='build-docker-image-x86',
                            input=source_output,
                            project=build_x86_project
                        ),
                        CodeBuildAction(
                            action_name='build-docker-image-arm',
                            input=source_output,
                            project=build_arm_project
                        )
                    ]
                ),
                StageProps(
                    stage_name='Manifest',
                    actions=[
                        CodeBuildAction(
                            action_name='create-manifest',
                            input=source_output,
                            project=build_manifest_project
                        )
                    ]
                )
            ]
        )

    def build_project(self, project_id, build_image, region, account, repo_name, image_tag):
        build_environment = BuildEnvironment(
            build_image=LinuxBuildImage.AMAZON_LINUX_2_3,
            privileged=True,
            environment_variables={
                'AWS_DEFAULT_REGION': BuildEnvironmentVariable(value=region),
                'AWS_ACCOUNT_ID':     BuildEnvironmentVariable(value=account),
                'IMAGE_REPO_NAME':    BuildEnvironmentVariable(value=repo_name),
                'IMAGE_TAG':          BuildEnvironmentVariable(value=image_tag)
            }
        )
        project = PipelineProject(self, project_id, environment=build_environment)
        project.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryPowerUser'))
        return project
        