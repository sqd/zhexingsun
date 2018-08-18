**客户端支持Windows 10(WSL) ([安装教程](https://zhuanlan.zhihu.com/p/24537874)), Linux, Mac**

假装自己是个HTTPS API的代理

HTTP请求会被封装进一个HTTPS包里发给远方的代理服务器。

这是一次真实的客户机和代理服务器之间的HTTPS通讯，和HTTPS API调用没有区别。

HTTPS握手在本地被劫持，`CONNECT`不会被真实地发送给代理服务器。也不会发生双层的握手。（即不会出现简单地把SOCKS类代理封装在SSL中时，能看到明显的`(SOCKS握手)－SSL握手－SSL payload`的特征情况）。

有意不支持HTTP长连接和相关技术（也是因为API服务器没有理由使用这个功能）。

代理服务器收到请求时，先检查`X-Proxy-Secret` header是否存在并匹配，否则伪装成正常网站（例如wordpress）。

**安全考虑：极度建议自己修改`forbidden.conf`，放上例如Jekyll, Wordpress, Laravel, 家里狗的照片之类的正常内容**

# 使用
- 客户机

1. `git clone https://github.com/sqd/zhexingsun.git && cd zhexingsun`
2. `setup_local_proxy.sh`
3. `./local_proxy.py -s your-server.com -x yourpassword -p 8080 --self-signed &` (若使用受信任的证书，请忽略`--self-signed`)
4. 浏览器将HTTP和SSL/TSL代理**都**设置为`127.0.0.1:8080`
5. 访问 [http://install_ca/](http://install_ca/) 添加本地根证书
6. 科学上网

- 服务器
1. `git clone https://github.com/sqd/zhexingsun.git && cd zhexingsun`
2. 设置密码
3. `mkdir -p certs && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout certs/ca.key -out certs/ca.crt` (实际使用请自备[证书](https://letsencrypt.org/))
4. `docker-compose up -d && disown` (或者自行安装[openresty](https://openresty.org/en/)并参照设置nginx.conf和证书)

# 配置
- 客户机
`local_proxy.py --help`

- 服务器
`password.conf`中设置密码

# 高级使用
`forbidden.conf`可随意更改为转发给任意伪装app(比如wordpress)

`reload.sh`动态重新加载新配置
