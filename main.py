
import os, sqlite3, uuid
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from .grading import estimate_centering_from_image, centering_score, estimated_grades

BASE = Path(__file__).resolve().parent.parent
DATA = BASE/"data"
UPLOADS = BASE/"app"/"static"/"uploads"
DATA.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)
DB = DATA/"cards.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","change-me")
app.config["MAX_CONTENT_LENGTH"] = 20*1024*1024
ALLOWED = {"jpg","jpeg","png","webp"}

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS cards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,set_name TEXT,card_number TEXT,language TEXT DEFAULT 'English',
        purchase_price REAL DEFAULT 0,grading_fee REAL DEFAULT 0,market_value REAL DEFAULT 0,
        grading_company TEXT,submission_status TEXT DEFAULT 'Raw',cert_number TEXT,actual_grade TEXT,
        front_image TEXT,back_image TEXT,front_lr TEXT,front_tb TEXT,back_lr TEXT,back_tb TEXT,
        centering_score REAL,corners_score REAL,edges_score REAL,surface_score REAL,
        estimated_psa INTEGER,estimated_bgs REAL,black_label_chance TEXT,confidence REAL,
        notes TEXT,created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")

def save_image(file, prefix):
    if not file or not file.filename: return None
    ext = file.filename.rsplit(".",1)[-1].lower()
    if ext not in ALLOWED: raise ValueError("Photo must be JPG, PNG, or WEBP")
    name = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
    file.save(UPLOADS/secure_filename(name))
    return name

@app.route("/")
def index():
    with db() as con:
        cards = con.execute("SELECT * FROM cards ORDER BY id DESC").fetchall()
        totals = con.execute("""SELECT COUNT(*) n,COALESCE(SUM(purchase_price),0) invested,
        COALESCE(SUM(grading_fee),0) fees,COALESCE(SUM(market_value),0) value FROM cards""").fetchone()
    return render_template("index.html",cards=cards,totals=totals)

@app.route("/add",methods=["POST"])
def add_card():
    try:
        front_name = save_image(request.files.get("front_image"),"front")
        back_name = save_image(request.files.get("back_image"),"back")
        front = estimate_centering_from_image(UPLOADS/front_name) if front_name else None
        back = estimate_centering_from_image(UPLOADS/back_name) if back_name else None
        cscore = centering_score(front,back)
        corners = float(request.form["corners_score"]) if request.form.get("corners_score") else None
        edges = float(request.form["edges_score"]) if request.form.get("edges_score") else None
        surface = float(request.form["surface_score"]) if request.form.get("surface_score") else None
        grades = estimated_grades(cscore,corners,edges,surface)
        confs = [x["confidence"] for x in [front,back] if x]
        conf = round(sum(confs)/len(confs),2) if confs else None
        def txt(r,k):
            if not r:return None
            a,b=r[k]; return f"{a:.1f}/{b:.1f}"
        with db() as con:
            con.execute("""INSERT INTO cards(name,set_name,card_number,language,purchase_price,grading_fee,market_value,
            grading_company,submission_status,front_image,back_image,front_lr,front_tb,back_lr,back_tb,
            centering_score,corners_score,edges_score,surface_score,estimated_psa,estimated_bgs,
            black_label_chance,confidence,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (request.form["name"].strip(),request.form.get("set_name",""),request.form.get("card_number",""),
             request.form.get("language","English"),float(request.form.get("purchase_price") or 0),
             float(request.form.get("grading_fee") or 0),float(request.form.get("market_value") or 0),
             request.form.get("grading_company",""),request.form.get("submission_status","Raw"),
             front_name,back_name,txt(front,"left_right"),txt(front,"top_bottom"),txt(back,"left_right"),
             txt(back,"top_bottom"),cscore,corners,edges,surface,grades["psa"],grades["bgs"],
             grades["black_label"],conf,request.form.get("notes","")))
        flash("Card added and estimate calculated.","success")
    except Exception as e:
        flash(f"Could not add card: {e}","error")
    return redirect(url_for("index"))

@app.route("/card/<int:card_id>/update",methods=["POST"])
def update_card(card_id):
    with db() as con:
        con.execute("""UPDATE cards SET grading_company=?,submission_status=?,cert_number=?,actual_grade=?,
        market_value=?,notes=? WHERE id=?""",(request.form.get("grading_company",""),
        request.form.get("submission_status","Raw"),request.form.get("cert_number",""),
        request.form.get("actual_grade",""),float(request.form.get("market_value") or 0),
        request.form.get("notes",""),card_id))
    flash("Card updated.","success")
    return redirect(url_for("index"))

@app.route("/card/<int:card_id>/delete",methods=["POST"])
def delete_card(card_id):
    with db() as con:
        row=con.execute("SELECT front_image,back_image FROM cards WHERE id=?",(card_id,)).fetchone()
        if row:
            for f in [row["front_image"],row["back_image"]]:
                if f:
                    try:(UPLOADS/f).unlink(missing_ok=True)
                    except:pass
        con.execute("DELETE FROM cards WHERE id=?",(card_id,))
    return redirect(url_for("index"))

@app.route("/health")
def health():
    return {"ok":True}

init_db()

if __name__=="__main__":
    app.run(host=os.environ.get("HOST","0.0.0.0"),port=int(os.environ.get("PORT","8000")))
