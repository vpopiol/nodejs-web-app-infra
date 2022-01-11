from typing_extensions import runtime
from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as lb
    # aws_sqs as sqs,
)
from constructs import Construct

class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, ecr_repo: ecr.Repository, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.repo_url = ecr_repo.repository_uri ## f'{self.account}.dkr.ecr.{self.region}.amazonaws.com/containers-multi-arch'
        # self.ecs_execution_role_arn = f'arn:aws:iam::{self.account}:role/ecsTaskExecutionRole'
        
        # Create VPC
        self.vpc = ec2.Vpc(self, "VPC")

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

        # ECS Execution Role
        self.ecs_execution_role = iam.Role(self, "EcsExecutionRole",
            description="ECS Execution Role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )

        # Cretate ALB
        self.alb = lb.ApplicationLoadBalancer(self, 'Alb',
            vpc=self.vpc,
            internet_facing=True,
        )

        self.alb_http_listener = self.alb.add_listener('AlbHttp', 
            port=80,
            default_action=lb.ListenerAction.fixed_response(
                status_code=200,
                content_type='text/plain',
                message_body='OK'
            )
        )

        # Create 2 instances
        self.create_ec2_instance("container_testing_x86_instance1", amzn_linux_x86_ami, "t2.medium")
        self.create_ec2_instance("container_testing_arm_instance1", amzn_linux_arm_ami, "t4g.medium")

        # Create ecs resources
        self.create_ecs()

    def get_ami(self, cpu_type):
        ami = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE,
            cpu_type=cpu_type)
        return ami

    def create_ec2_instance(self, name, ami, instance_type):

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
        instance = ec2.Instance(self, name,
            vpc = self.vpc,
            instance_name=name,
            instance_type=ec2.InstanceType(instance_type),
            machine_image=ami,
            role=self.instance_role,
            # security_group=self.sg,
            user_data=user_data
        )
        # instance.node.add_dependency(self.vpc)
        return instance

    def create_ecs(self):        
        # Create ECS Cluster
        cluster = ecs.Cluster(self, "FargateCluster",
            vpc=self.vpc,
            cluster_name=self.stack_name
        )
        # cluster.node.add_dependency(self.vpc)

        # Create security group for ECS tasks
        sg = ec2.SecurityGroup(self, "SecurityGroup", vpc=self.vpc, description="Allow 8080")
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(8080))
        sg.node.add_dependency(self.vpc)

        # Create task definitions
        td_x86=self.create_task_definition("X86_64")
        td_arm=self.create_task_definition("ARM64")

        #Create services
        svx_x86=self.create_ecs_service(td_x86, 'svc-x86', sg, cluster, 110)
        svx_arm=self.create_ecs_service(td_arm, 'svc-arm', sg, cluster, 120)

    def create_task_definition(self, architecture):
        task_definition = ecs.TaskDefinition(self, f'task_definition_{architecture}',
            compatibility=ecs.Compatibility.FARGATE,
            network_mode=ecs.NetworkMode.AWS_VPC,
            memory_mib="512",
            cpu="256",
            execution_role=self.ecs_execution_role
        )
        task_definition.add_container(f'container-{architecture}',
            container_name=architecture,
            image=ecs.ContainerImage.from_registry(self.repo_url),
            port_mappings=[ecs.PortMapping(container_port=8080, host_port=8080, protocol=ecs.Protocol.TCP)]
        )
        task_definition.node.default_child.add_property_override("RuntimePlatform", {"cpuArchitecture": architecture, "operatingSystemFamily": "LINUX"})

        return task_definition

    def create_ecs_service(self, task_definition, name, security_group, cluster, target_priority):
        ecs_svc = ecs.FargateService(self, name,
            cluster=cluster,
            assign_public_ip=True,
            task_definition=task_definition,
            security_groups=[security_group],
            vpc_subnets=ec2.SubnetSelection(subnets=self.vpc.select_subnets(one_per_az=True).subnets),
            desired_count=1
        )
        # ecs_svc.node.add_dependency(self.vpc)

        # Configure ALB
        container_name=ecs_svc.task_definition.default_container.container_name
        lb_target = ecs_svc.load_balancer_target(container_name=container_name)
        self.alb_http_listener.add_targets(f'EcsServiceTarget{container_name}', 
            port=80,
            targets=[lb_target],
            conditions=[lb.ListenerCondition.path_patterns([f'/ecs/{name}'])],
            priority=target_priority
        ) 
        return ecs_svc