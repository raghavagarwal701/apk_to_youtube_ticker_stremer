commands

start screen
screen -S "name"
reattch to screen
screen -r 11984.apk_to_youtube_server



to start nginx
go to nginx directory: nginx-1.27.1
in that run 
./configure --add-module=nginx-rtmp-module
make
sudo make install


nginx config file 
sudo nano /usr/local/nginx/conf/nginx.conf

test nginx file
sudo /usr/local/nginx/sbin/nginx -t

start nginx
sudo /usr/local/nginx/sbin/nginx

if it gives nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
then run
sudo lsof -i :80
to kill it run
sudo systemctl stop apache2

check nginx status 
ps aux | grep nginx

check nginx log 
tail /usr/local/nginx/logs/error.log



curl -X POST http://65.0.138.138:1233/stop_stream \ 
-H "Content-Type: application/json; charset=UTF-8" \
-d '{
  "stream_name": "my_stream_key"
}'

curl -X POST http://65.0.138.138:1233/start_stream \
-H "Content-Type: application/json; charset=UTF-8" \
-d '{
  "youtube_url": "https://youtube.com/example",
  "stream_name": "my_stream_key"
}'


