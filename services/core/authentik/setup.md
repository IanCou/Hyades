mkdir -p /data/authentik/{postgres,media,certs,templates}

chown -R 70:70 /opt/data/authentik/postgres

docker exec -it authentik-server-1 ak changepassword akadmin
