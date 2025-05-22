from flask import Blueprint, render_template, redirect

bp = Blueprint("pages", __name__)

@bp.route("/")
def home():
    #return "<a href='http://41.196.252.205:8000/about'> <h1 style='color:orange'> Hello, Home! </h1> </a>"
    #return "<a href='/about'> <h1 style='color:orange'> Hello, Home! </h1> </a>"
    return render_template("pages/home.html")

@bp.route("/about")
def about():
    #return "<a href='http://41.196.252.205:8000/'>  <h1 style='color:purple'>  Hello, About! </h1> </a>"
    # return "<a href='/'>  <h1 style='color:purple'>  Hello, About! </h1> </a>"
    return render_template("pages/about.html") 
    
@bp.route("/printer")
def printer():
    return redirect("http://192.168.1.11:631", code=302) #using nmap tool (nmap -sS <printer-local-ip>) we tought that my printer uses ipp protocol on port 631/tcp 