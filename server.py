import requests
import http.server
import os
import subprocess


class base_case(object):
    """Parent for case handlers."""

    def index_path(self, handler):
        return os.path.join(handler.full_path, "index.html")

    def test(self, handler):
        assert False, "Not implemented."

    def act(self, handler):
        assert False, "Not implemented."


class case_cgi_file(base_case):
    """Something runnable."""

    def test(self, handler):
        return os.path.isfile(handler.full_path) and handler.full_path.endswith(".py")

    def act(self, handler):
        handler.run_cgi(handler.full_path)


class case_directory_no_index_file(base_case):
    """Serve listing for a directory without an index.html page"""

    def index_path(self, handler):
        return (
            os.path.join(handler.full_path, "index.html") and handler.full_path != "/"
        )

    def test(self, handler):
        return os.path.isdir(handler.full_path) and not os.path.isfile(
            self.index_path(handler)
        )

    def act(self, handler):
        print(handler.full_path)
        handler.list_dir(handler.full_path)


class case_directory_index_file(base_case):
    """Serve index.html page for a directory"""

    def index_path(self, handler):
        return os.path.join(handler.full_path, "index.html")

    def test(self, handler):
        return os.path.isdir(handler.full_path) and os.path.isfile(
            self.index_path(handler)
        )

    def act(self, handler):
        handler.handle_file(handler, self.index_path(handler))


class case_no_file(base_case):
    """File or directory does not exist."""

    def test(self, handler):
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        raise Exception(f"{handler.path} not found.")


class case_existing_file(base_case):
    """File exists."""

    def test(self, handler):
        return os.path.isfile(handler.full_path)

    def act(self, handler):
        handler.handle_file(handler, handler.full_path)


class case_always_fail(base_case):
    """Base case if nothing else worked."""

    def test(self, handler):
        return True

    def act(self, handler):
        raise Exception(f"Unknown object {handler.path}")

class RequestHandler(http.server.BaseHTTPRequestHandler):
    """
    If requested path maps to a file, that file is served.
    If anything goes wrong, an error page is constructed
    """

    Cases = [
        case_no_file,
        case_cgi_file,
        case_existing_file,
        case_directory_index_file,
        case_directory_no_index_file,
        case_always_fail,
    ]

    # Page to send back

    Root_Page: str = """\
        <html>
        <body>
        <table>
        <tr>  <td>Header</td>         <td>Value</td>          </tr>
        <tr>  <td>Date and time</td>  <td>{date_time}</td>    </tr>
        <tr>  <td>Client host</td>    <td>{client_host}</td>  </tr>
        <tr>  <td>Client port</td>    <td>{client_port}s</td> </tr>
        <tr>  <td>Command</td>        <td>{command}</td>      </tr>
        <tr>  <td>Path</td>           <td>{path}</td>         </tr>
        </table>
        </body>
        </html>
        """

    
    # Handle a GET request

    def do_GET(self):

        try:
            self.full_path: str = os.getcwd() + self.path

            for case in self.Cases:
                handler = case()
                if handler.test(self):
                    handler.act(self)
                    break

        except Exception as msg:
            self.handle_error(msg)

    def handle_file(self, handler, full_path):
        try:
            with open(full_path, "r") as reader:
                content: str = reader.read()
            handler.send_content(content)
        except IOError as msg:
            msg = f"{full_path} cannot be read: {msg}"
            handler.handle_error(msg)

    def create_root_page(self):
        values = {
            "date_time": self.date_time_string(),
            "client_host": self.client_address[0],
            "client_port": self.client_address[1],
            "command": self.command,
            "path": self.path,
        }
        page: str = self.Root_Page.format(**values)
        return page

    def handle_error(self, msg):
        Error_Page: str = """\
        <html>
        <body>
        <h1>Error accessing {path}</h1>
        <p>{msg}</p>
        </body>
        </html>
        """
        content: str = Error_Page.format(path=self.path, msg=msg)
        self.send_content(content, 404)

    def send_content(self, content: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def list_dir(self, full_path):
        Listing_Page: str = """\
        <html>
        <body>
        <ul>
        {0}
        </ul>
        </body>
        </html>"""

        try:
            entries = os.listdir(full_path)
            bullets = [
                "<li>{0}</li>".format(e) for e in entries if not e.startswith(".")
            ]
            page = Listing_Page.format("\n".join(bullets))
            self.send_content(page)

        except OSError as msg:
            msg: str = f"{self.path} cannot be listed: {msg}"
            self.handle_error(msg)

    def run_cgi(self, full_path):
        cmd = "python3 " + full_path
        data: str = str(subprocess.run(cmd).stdout)
        self.send_content(data)


def main():
    server = http.server.HTTPServer(
        server_address=("", 8080), RequestHandlerClass=RequestHandler
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
