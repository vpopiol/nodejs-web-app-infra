from typing_extensions import runtime
from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as lb,
)
from constructs import Construct

class InfraVpcStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC
        self.vpc = ec2.Vpc(self, "VPC")

        # Cretate alb
        alb = lb.ApplicationLoadBalancer(self, 'Alb',
            vpc=self.vpc,
            internet_facing=True,
        )

        # Add http listener to alb
        self.alb_http_listener = alb.add_listener('AlbHttp', 
            port=80,
            default_action=lb.ListenerAction.fixed_response(
                status_code=200,
                content_type='text/plain',
                message_body='OK'
            )
        )

