cd DeathStarBench/socialNetwork/ &&
sudo docker-compose up -d &&
sed -i -e 's/[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}/127.0.0.1/' scripts/init_social_graph.py &&
python3 scripts/init_social_graph.py &&
cd wrk2/ &&
sed -i ' 1 s/.*/& -fPIC/' Makefile &&
make clean && make
