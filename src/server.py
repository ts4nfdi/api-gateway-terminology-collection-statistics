import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import collectionStats as cS

providers = cS.get_providers()

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed_url = urlparse(self.path)
        try:
            if parsed_url.path == "/stats":
                collections = self.handle_stats(parsed_url)
            elif parsed_url.path == "/stats/all":
                collections = self.handle_stats_all(parsed_url)
            else:
                self.send_json(404, {"error": "Not found"})
                return

            collections_stats, collection_errors = cS.calculate_stats_for_collections(providers, collections)
            cS.write_to_db(collections_stats)
            print(collections_stats)
            self.send_success_message(collection_errors)

        except Exception as e:
            self.send_json(500, {"error": "Internal error"})
            return


    def handle_stats_all(self, parsed_url):
        collections = cS.create_selected_collection_list(include_all=True)
        return collections


    def handle_stats(self, parsed_url):
        params = parse_qs(parsed_url.query)
        collection_ids = params.get("collection", [])
        collections = cS.create_selected_collection_list(collection_ids)
        return collections

    def send_success_message(self, collection_errors):
        if collection_errors:
            self.send_json(200, {
                "message": "Successfully inserted collection stats into DB."
                           " For some collections no statistics could be generated.",
                "errors": collection_errors
            })
        else:
            self.send_json(200, {
                "message": "Successfully inserted collection stats into DB."
                           " For all collections statistics could be generated.",
                "errors": []
            })

    def send_json(self, status_code, data):
        response = json.dumps(data).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()

        self.wfile.write(response)

server = HTTPServer(("0.0.0.0", 8000), Handler)

print("Server running on port 8000...")
server.serve_forever()
