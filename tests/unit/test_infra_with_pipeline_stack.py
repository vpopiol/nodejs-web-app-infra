import aws_cdk as core
import aws_cdk.assertions as assertions

from infra_with_pipeline.infra_with_pipeline_stack import InfraWithPipelineStack

# example tests. To run these tests, uncomment this file along with the example
# resource in infra_with_pipeline/infra_with_pipeline_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = InfraWithPipelineStack(app, "infra-with-pipeline")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
