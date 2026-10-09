from awsglue.context import GlueContext
from awsglue.job import Job
import com.amazonaws.services.s3.AmazonS3ClientBuilder as Builder

glueContext = GlueContext(SparkContext.getOrCreate())
job = Job(glueContext)


def build_client():
    return Builder.defaultClient()
