from flask import Blueprint

bp = Blueprint("pages", __name__)

@bp.route("/")
def home():
    #return "<a href='http://41.196.252.205:8000/about'> <h1 style='color:orange'> Hello, Home! </h1> </a>"
    return "<a href='/about'> <h1 style='color:orange'> Hello, Home! </h1> </a>"

@bp.route("/about")
def about():
    #return "<a href='http://41.196.252.205:8000/'>  <h1 style='color:purple'>  Hello, About! </h1> </a>"
    return "<a href='/'>  <h1 style='color:purple'>  Hello, About! </h1> </a>"
    
