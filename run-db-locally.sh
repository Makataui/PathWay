docker run -d \
    -p 5432:5432 \
    --name postgres_pathway \
    -e POSTGRES_PASSWORD=1234 \
    -e POSTGRES_USER=postgres \
    postgres