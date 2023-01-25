import tornado.web
from tornado import httpserver as hs
from tornado import httpclient as hc
import threading
import asyncio
import time
from tornado.netutil import bind_sockets


class Chain:
    def __init__(self, name, ip, port):
        self.name = name
        self.ip = ip
        self.port = port
        self.nowserver = None
        self.network = []
        #self.pos = 0
        self.httpclient = hc.HTTPClient()
        self.role = 0

    def main(self):
        threading.Thread(target=asyncio.run, args=(self.server(),)).start()
        self.client()

    def client(self):
        self.add_first_node()
        start_time = time.time()
        while True:
            # добавляем новых клиентов
            self.update_info(self.httpclient)
            # обновляем мастер сервер при падении текущего и удаляем умерший мастер из списка
            if not self.check_connection(self.httpclient, self.nowserver):
                self.network.pop(0)
                #self.pos += 1
                self.nowserver = self.network[0]
                print("server died")
                print(f"connect to {self.nowserver}")

            if self.nowserver == f"http://{self.ip}:{self.port}":
                self.role = 1

            #if time.time() - start_time > 3:
                #start_time = time.time()
            self.delete_offline(self.httpclient)

            print(self.network)
            print(self.role)
            #print(self.nowserver)

    async def server(self):
        await self.sub_serv()
        await asyncio.Event().wait()

    async def sub_serv(self):
        app = tornado.web.Application(handlers=[
            (r"/", BaseHandler),
            (r"/update", SecondHandler)])
        app.network = self.network
        app.chain = self
        server = hs.HTTPServer(app)
        sockets = bind_sockets(self.port)
        server.add_sockets(sockets)

    def add_first_node(self):
        print("add first node to connect:")
        self.network.append(str(input()))
        # http://localhost:8888
        self.nowserver = self.network[0]
        self.update_connection(self.httpclient)

    def update_connection(self, http_client):
        try:
            response = http_client.fetch(self.nowserver, method="POST", body=f"http://localhost:{self.port}".encode())
        except Exception as e:
            print("Error: %s" % e)
        else:
            for i in response.body.decode().split(sep=','):
                if self.network.count(i) == 0 and i != '':
                    self.network.append(i)

    def update_info(self, http_client):
        try:
            response = http_client.fetch(f"{self.nowserver}/update", method="GET")
        except Exception as e:
            print("Error: %s" % e)
        else:
            for i in response.body.decode().split(sep=','):
                if self.network.count(i) == 0 and i != '':
                    self.network.append(i)

    def delete_offline(self, http_client):
        try:
            response = http_client.fetch(f"{self.nowserver}/update", method="GET")
        except Exception as e:
            print("Error: %s" % e)
        else:
            for i in response.body.decode().split(sep=','):
                if not self.check_connection(self.httpclient, i):
                    while self.network.count(i) > 0 and i != '':
                        ind = self.network.index(i)
                        self.network.pop(ind)
                if (not self.check_connection(self.httpclient, f"http://{self.ip}:{self.port}")) and self.role == 1:
                    while self.network.count(i) > 0 and i != '':
                        ind = self.network.index(i)
                        self.network.pop(ind)


    def check_connection(self, http_client, node):
        try:
            http_client.fetch(node, method="GET")
        except Exception:
            return False
        else:
            return True


class BaseHandler(tornado.web.RequestHandler):
    def post(self):
        if self.application.chain.nowserver != self.request.body.decode():
            self.application.chain.network.append(self.request.body.decode())
        for i in self.application.network:
            self.write(f"{i},")

    def get(self):
        self.write("alive")


class SecondHandler(tornado.web.RequestHandler):
    def get(self):
        if self.application.chain.nowserver != f"http://localhost:{self.application.chain.port}":
            self.application.chain.update_info(self.application.chain.httpclient)
        for i in self.application.network:
            self.write(f"{i},")