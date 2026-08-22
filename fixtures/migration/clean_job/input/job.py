from awsglue.context import GlueContext
from awsglue.job import Job
import boto3

glueContext = GlueContext(SparkContext.getOrCreate())
job = Job(glueContext)


def main():
    client = boto3.client("s3")
    return client
