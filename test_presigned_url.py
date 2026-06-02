from datetime import timedelta

from minio import Minio

client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False,
)

url = client.presigned_get_object(
    "package-images",
    "RAG Summary.PNG",
    expires=timedelta(hours=1),
)

print(url)
