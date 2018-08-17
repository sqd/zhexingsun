# 者行孙
假装自己是个HTTPS API的代理

HTTP请求会被封装进一个HTTPS包里发给远方的代理服务器。

这是一次真实的客户机和代理服务器之间的HTTPS通讯，和HTTPS API调用没有区别。

HTTPS握手在本地被劫持，`CONNECT`不会被真实地发送给代理服务器。

有意不支持HTTP长连接和相关技术（也是因为API服务器没有理由使用这个功能）

# 使用
- 客户机

0. 配置服务器地址和密码
1. `git clone https://github.com/sqd/zhexingsun.git && cd zhexingsun`
2. `setup_local_proxy.sh`
3. `(./local_proxy.py 8080 &) && disown`
4. 浏览器将HTTP和SSL/TSL代理**都**设置为`127.0.0.1:8080`
5. 访问 [http://install_ca/](http://install_ca/) 添加本地根证书
6. 科学上网

- 服务器
0. 配置密码
1. `git clone https://github.com/sqd/zhexingsun.git && cd zhexingsun`
2. `mkdir -p certs && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout certs/ca.key -out certs/ca.crt` (实际使用请自备[证书](https://letsencrypt.org/))
3. `docker-compose up -d && disown` (或者自行安装[openresty](https://openresty.org/en/)并参照设置nginx.conf和证书)

# 配置
- 客户机
`local_proxy.py`中`PROXY_SERVER_ADDRESS = 'localhost'`更改`localhost`为服务器地址, `PROXY_SERVER_SECRET_KEY = '1234'`更改`1234`为密码

- 服务器
`nginx.conf`中`if ngx.req.get_headers()["X-Proxy-Secret"] ~= "1234" then`更改`1234`为密码

# 高级使用
nginx的`/forbidden_path_no_accidental_name_collision`可随意转发给任意伪装app(比如wordpress)
