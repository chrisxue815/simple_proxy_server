import proxy_server


def main():
    with proxy_server.Proxy() as proxy:
        proxy.serve_forever()


if __name__ == '__main__':
    main()
