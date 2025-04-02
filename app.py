from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/contributions")
def get_contributions():
    data = {
        "labels": ["2025-03-25", "2025-03-26", "2025-03-27", "2025-03-28", "2025-03-29", "2025-03-30", "2025-03-31"],
        "members": {
            "Anson": [2, 1, 3, 5, 4, 1, 9],
            "Yu Sang": [3, 2, 0, 6, 7, 9, 3],
            "Tsz To": [1, 0, 2, 1, 0, 2, 3],
            "Yuk Yu": [0, 1, 1, 0, 2, 1, 2]
        }
    }
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
