from flask import Flask, render_template,request, redirect, url_for, make_response
from flask_ngrok import run_with_ngrok
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from nlppreprocess import NLP
import pandas as pd
# pip install pdfminer.six==20181108
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
import io
from transformers import pipeline
from flask_sqlalchemy import SQLAlchemy
import json
import requests
import pdfkit
from flask_bcrypt import Bcrypt
nlp = pipeline('question-answering')    
app = Flask(__name__)
obj = NLP()
db = SQLAlchemy(app)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]= False
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///db.sqlite3'
run_with_ngrok(app)
bcrypt = Bcrypt(app)



class User(db.Model):
    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Username = db.Column(db.String(16), nullable=False)
    Password = db.Column(db.String(16), nullable=False)
 


class Article(db.Model):
    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Title = db.Column(db.String(50), nullable=False)
    Content = db.Column(db.String(10000), nullable=False)



@app.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/dashboard', methods=['POST'])
def dashboard():
    
    username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(Username=username).first()

    articles = Article.query.all()
    
    if user and user.Password==password:
        return render_template('dashboard.html', articles=articles)
    else :
        return render_template('login.html', warning='Please enter correct username and password')

@app.route('/fulldashboard', methods=['GET', 'POST'])
def fulldashboard():
    
    articles = Article.query.all()
    return render_template('fulldashboard.html', articles=articles)




    
@app.route('/wcloud',methods=['GET', 'POST']) 
def wcloud():
    file = open("doc.txt","r") 
    text=file.read() 
    wordcloud = WordCloud(width = 550, height = 500, 
        				background_color ='white',  
        				min_font_size = 10).generate(text) 
        
        # plot the WordCloud image					 
    plt.figure(figsize = (8, 8), facecolor = None) 
    plt.imshow(wordcloud) 
    plt.axis("off") 
    plt.tight_layout(pad = 0) 
    plt.savefig('static/images/new_plot.png')
    return render_template('wcloud.html',name = 'new_plot', url ='static/images/new_plot.png')

@app.route('/ques_ans',methods=['GET', 'POST'])
def ques_ans():
    file = open("doc.txt","r") 
    ques= request.form["ques"]
    text=file.read() 
    ans=nlp({
    'question': ques,
    'context': text})
    new=ans['answer']
   
    return render_template('qna.html',answer=new)

@app.route('/uploader',methods=['GET', 'POST']) ##called when new file is uploaded in UI
def uploader():
   if request.method == 'POST':
       
      #pdf = request.files['file']
        fp = request.files['file']
        file = open("doc.txt","wb")
        #fp = open('Business Proposal.pdf', 'rb')
        rsrcmgr = PDFResourceManager()
        retstr = io.StringIO()
        #print(type(retstr))
        codec = 'utf-8'
        laparams = LAParams()
        device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        
        page_no = 0
        for pageNumber, page in enumerate(PDFPage.get_pages(fp.stream)):
            if pageNumber==page_no :
                interpreter.process_page(page)
        
                data = retstr.getvalue()
                
                text=obj.process(data)
                file.write(text.encode('utf-8'))
                ok='file ended \n\n\n'
                file.write(ok.encode('utf-8'))
                retstr.truncate(0)
                retstr.seek(0)

            page_no += 1
        return render_template('selectprocess.html')
    
   else:
       return render_template('upload.html', warning='not uploaded')
   
    
@app.route("/find", methods=['POST'])
def find():
    #Moving forward code
    return render_template('search.html');

@app.route("/found", methods=['POST'])
def found():
    #Moving forward code
    key = "AIzaSyAKaAHSXiYBZvdFN_yL_fww6cgiZDGa7lc"
    cx = "012539925451565010534:i6bztbqo0pn"

    keywords = request.form['keywords']
    noofresults = int(request.form['noofresults'])
    # indexid = int(request.form['indexid'])

    url = "https://www.googleapis.com/customsearch/v1"
    parameters = {"q": keywords,
                  "cx": cx,
                  "key": key,
              }

    page = requests.request("GET", url, params=parameters)
    results = json.loads(page.text)

    def process_search(results):
        link_list = [item["link"] for item in results["items"]]
        df = pd.DataFrame(link_list, columns=["link"])
        df["title"] = [item["title"] for item in results["items"]]
        df["snippet"] = [item["snippet"] for item in results["items"]]
        return df[:noofresults]
    df = process_search(results)
    return render_template('search.html',tables=[df.to_html(render_links=True,classes=['table table-bordered'])]);

@app.route("/upload/", methods=['POST'])
def upload():
    #Moving forward code
    return render_template('upload.html');

@app.route("/editor", methods=['GET', 'POST'])
def editor():
    if(request.method=="POST"):
        Title = request.form.get("title")
        Content = request.form.get("content")
        entry = Article(Title=Title, Content=Content)
        db.session.add(entry)
        db.session.commit()
        return redirect(url_for("fulldashboard"))
    return render_template('editor.html', methods=['GET', 'POST'])

@app.route("/selection", methods=['POST'])
def selection():
    return render_template("selection.html")

@app.route("/pdfdashboard", methods=['POST'])
def pdfdashboard():
    return render_template("pdfdashboard.html")

@app.route("/editor/<int:ID>")
def post(ID):
    article = Article.query.get_or_404(ID)
    return render_template("editarticle.html", ID=article.ID, Title=article.Title, Content=article.Content)

if __name__ == "__main__":
    # app.run(debug=True,use_reloader=False)
    app.run()
