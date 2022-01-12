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

class InfraEcsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, ecr_repo: ecr.Repository, vpc: ec2.Vpc, alb_http_listener: lb.ApplicationListener, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.repo_url = ecr_repo.repository_uri ## f'{self.account}.dkr.ecr.{self.region}.amazonaws.com/containers-multi-arch'
        # self.ecs_execution_role_arn = f'arn:aws:iam::{self.account}:role/ecsTaskExecutionRole'
        
        self.vpc = vpc
        self.alb_http_listener = alb_http_listener

        # ECS Execution Role
        self.ecs_execution_role = iam.Role(self, "EcsExecutionRole",
            description="ECS Execution Role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )

        # Create ecs resources
        self.create_ecs()

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
        svc_x86=self.create_ecs_service(
            task_definition=td_x86, 
            name='svc-x86', 
            security_group=sg, 
            cluster=cluster, 
            target_priority=210,
            uri='/ecs/x86'
        )
        svc_arm=self.create_ecs_service(
            task_definition=td_arm, 
            name='svc-arm', 
            security_group=sg, 
            cluster=cluster, 
            target_priority=220,
            uri='/ecs/arm'
        )

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

    def create_ecs_service(self, task_definition, name, security_group, cluster, target_priority, uri):
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
            conditions=[lb.ListenerCondition.path_patterns([uri])],
            priority=target_priority
        ) 
        return ecs_svc