from typing_extensions import runtime
from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as lb,
    aws_autoscaling as autoscaling
    # aws_sqs as sqs,
)
from constructs import Construct

class InfraEc2Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, ecr_repo: ecr.Repository, vpc: ec2.Vpc, alb_http_listener: lb.ApplicationListener, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.repo_url = ecr_repo.repository_uri ## f'{self.account}.dkr.ecr.{self.region}.amazonaws.com/containers-multi-arch'
        # self.ecs_execution_role_arn = f'arn:aws:iam::{self.account}:role/ecsTaskExecutionRole'
        
        # Create VPC
        self.vpc = vpc

        # AMZ Lunux 2 AMIs for X86 and arm
        amzn_linux_x86_ami = self.get_ami(ec2.AmazonLinuxCpuType.X86_64)
        amzn_linux_arm_ami = self.get_ami(ec2.AmazonLinuxCpuType.ARM_64)

        # Role for EC2s allowing ECR ans SSM (for session manager)
        self.instance_role = iam.Role(self, "Ec2Role",
            description="Instance role to allow to pull container images",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("EC2InstanceProfileForImageBuilderECRContainerBuilds"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMPatchAssociation")
            ]
        )

        # Add http listener to alb
        self.alb_http_listener = alb_http_listener

        # Create 2 autoscaling groups
        self.create_asg(
            name="container_testing_x86", 
            ami=amzn_linux_x86_ami, 
            instance_type="t2.medium",
            uri='/ec2/x86', 
            target_priority=110
        )
        self.create_asg(
            name="container_testing_arm", 
            ami=amzn_linux_arm_ami, 
            instance_type="t4g.medium",
            uri='/ec2/arm', 
            target_priority=120
        )

    def get_ami(self, cpu_type):
        ami = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE,
            cpu_type=cpu_type)
        return ami

    def create_asg(self, name, ami, instance_type, target_priority, uri):

        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1",
            "sudo yum update",
            "sudo amazon-linux-extras install -y docker",
            "sudo service docker start",
            "sudo usermod -a -G docker ec2-user",
            f'aws ecr get-login-password --region {self.region} |  docker login --username AWS --password-stdin {self.repo_url}',
            f'docker run -d -p 8080:8080 {self.repo_url}:latest',
            f'curl localhost:8080/hello'
        )

        # Create autoscaling group
        asg = autoscaling.AutoScalingGroup(self, f'ASG_{name}',
            auto_scaling_group_name=name,
            vpc=self.vpc,
            instance_type=ec2.InstanceType(instance_type),
            machine_image=ami,
            role=self.instance_role,
            user_data=user_data
        )

        self.alb_http_listener.add_targets(f'AsgTarget{name}', 
            port=8080, 
            targets=[asg],
            conditions=[lb.ListenerCondition.path_patterns([uri])],
            priority=target_priority
        )

