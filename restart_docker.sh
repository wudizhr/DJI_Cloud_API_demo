docker stop emqx
docker remove emqx
docker run -d --name emqx --network host emqx:5.0.20