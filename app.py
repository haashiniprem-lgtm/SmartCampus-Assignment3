import os, uuid
from flask import Flask, request, redirect, url_for, render_template, jsonify
import psycopg

app = Flask(__name__)
DB = os.getenv("DATABASE_URL", "postgresql://campus:campus123@db:5432/campusdb")

def db():
    return psycopg.connect(DB)

def init():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS facilities(id SERIAL PRIMARY KEY,name TEXT UNIQUE,building TEXT,capacity INT)")
        c.execute("""CREATE TABLE IF NOT EXISTS bookings(id TEXT PRIMARY KEY,facility_id INT REFERENCES facilities(id),
          requester TEXT,role TEXT,start_at TIMESTAMP,end_at TIMESTAMP,status TEXT,created_at TIMESTAMP DEFAULT now())""")
        c.execute("""CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY,facility_id INT REFERENCES facilities(id),
          description TEXT,category TEXT,priority TEXT,assignee TEXT DEFAULT 'Unassigned',status TEXT DEFAULT 'Intake',
          inspection TEXT DEFAULT '',resolution TEXT DEFAULT '',version INT DEFAULT 1,event_id TEXT UNIQUE,
          created_at TIMESTAMP DEFAULT now())""")
        c.execute("""CREATE TABLE IF NOT EXISTS approvals(id SERIAL PRIMARY KEY,booking_id TEXT REFERENCES bookings(id),
          approver TEXT,decision TEXT,reason TEXT,created_at TIMESTAMP DEFAULT now())""")
        c.execute("""CREATE TABLE IF NOT EXISTS audit(id SERIAL PRIMARY KEY,actor TEXT,action TEXT,record_type TEXT,
          record_id TEXT,created_at TIMESTAMP DEFAULT now())""")
        c.execute("""INSERT INTO facilities(name,building,capacity) VALUES
          ('AI Lab','Block A',40),('Seminar Hall','Block B',100),('Robotics Lab','Block C',25)
          ON CONFLICT(name) DO NOTHING""")

@app.before_request
def ready():
    if not getattr(app, "_ready", False):
        init()
        app._ready = True

def log(c, actor, action, typ, rid):
    c.execute("INSERT INTO audit(actor,action,record_type,record_id) VALUES(%s,%s,%s,%s)",(actor,action,typ,rid))

def suggest(s):
    x=s.lower()
    category = "Plumbing" if any(w in x for w in ("water","leak","pipe")) else "Electrical" if any(w in x for w in ("power","socket","sparking")) else "HVAC" if any(w in x for w in ("cooling","air conditioner","ac")) else "General"
    priority = "Urgent" if any(w in x for w in ("smoke","fire","flood","sparking")) else "High" if any(w in x for w in ("leak","power","broken")) else "Normal"
    return category,priority

@app.get("/")
def home():
    with db() as c:
        facilities=c.execute("SELECT * FROM facilities ORDER BY id").fetchall()
        bookings=c.execute("SELECT b.id,f.name,b.requester,b.status,b.start_at,b.end_at FROM bookings b JOIN facilities f ON f.id=b.facility_id ORDER BY b.created_at DESC").fetchall()
        tickets=c.execute("SELECT t.id,f.name,t.description,t.category,t.priority,t.status,t.version,t.event_id FROM tickets t JOIN facilities f ON f.id=t.facility_id ORDER BY t.created_at DESC").fetchall()
        approvals=c.execute("SELECT booking_id,approver,decision,reason FROM approvals ORDER BY id DESC").fetchall()
        audits=c.execute("SELECT actor,action,record_type,record_id FROM audit ORDER BY id DESC LIMIT 10").fetchall()
    return render_template("index.html",facilities=facilities,bookings=bookings,tickets=tickets,approvals=approvals,audits=audits)

@app.post("/book")
def book():
    fid=request.form.get("facility_id",type=int); name=request.form.get("requester","Student"); role=request.form.get("role","Student")
    start=request.form.get("start_at"); end=request.form.get("end_at")
    if not fid or not start or not end or end<=start: return "400: Invalid booking time range",400
    bid="B-"+uuid.uuid4().hex[:7].upper()
    with db() as c:
        c.execute("SELECT pg_advisory_xact_lock(%s)",(fid,))
        old=c.execute("""SELECT id FROM bookings WHERE facility_id=%s AND status IN ('Requested','Approved','Confirmed')
          AND start_at < %s AND end_at > %s LIMIT 1""",(fid,end,start)).fetchone()
        if old: return "409 Conflict: overlapping reservation already exists.",409
        status="Confirmed" if role=="Facility Manager" else "Requested"
        c.execute("INSERT INTO bookings(id,facility_id,requester,role,start_at,end_at,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",(bid,fid,name,role,start,end,status))
        log(c,name,"BOOKING_CREATED","booking",bid)
    return redirect(url_for("home"))

@app.post("/ticket")
def ticket():
    fid=request.form.get("facility_id",type=int); desc=request.form.get("description","").strip(); event=request.form.get("event_id","").strip() or uuid.uuid4().hex
    if not fid or not desc: return "400: Facility and description required",400
    cat,pri=suggest(desc); tid="T-"+uuid.uuid4().hex[:7].upper()
    with db() as c:
        old=c.execute("SELECT id FROM tickets WHERE event_id=%s",(event,)).fetchone()
        if old: return "Duplicate event ignored. Existing ticket: "+old[0],200
        c.execute("INSERT INTO tickets(id,facility_id,description,category,priority,event_id) VALUES(%s,%s,%s,%s,%s,%s)",(tid,fid,desc,cat,pri,event))
        log(c,"Reporter","TICKET_CREATED","ticket",tid)
    return redirect(url_for("home"))

@app.post("/approve/<bid>")
def approve(bid):
    actor=request.form.get("actor","Approver"); role=request.form.get("role","Student"); decision=request.form.get("decision","Approved"); reason=request.form.get("reason","").strip()
    if role not in ("Department Approver","Administrator"): return "403 Forbidden: approval role required",403
    if not reason: return "400: Reason required",400
    with db() as c:
        if not c.execute("SELECT id FROM bookings WHERE id=%s",(bid,)).fetchone(): return "404: Booking not found",404
        c.execute("INSERT INTO approvals(booking_id,approver,decision,reason) VALUES(%s,%s,%s,%s)",(bid,actor,decision,reason))
        c.execute("UPDATE bookings SET status=%s WHERE id=%s",("Approved" if decision=="Approved" else "Cancelled",bid))
        log(c,actor,"BOOKING_"+decision.upper(),"booking",bid)
    return redirect(url_for("home"))

@app.post("/ticket/<tid>/update")
def update(tid):
    actor=request.form.get("actor","Technician"); role=request.form.get("role","Maintenance Technician")
    status=request.form.get("status","Inspection"); version=request.form.get("version",type=int)
    inspection=request.form.get("inspection",""); resolution=request.form.get("resolution","")
    if status=="Closed" and role not in ("Facility Manager","Administrator"): return "403 Forbidden: manager role required to close",403
    with db() as c:
        row=c.execute("SELECT version FROM tickets WHERE id=%s FOR UPDATE",(tid,)).fetchone()
        if not row: return "404: Ticket not found",404
        if version != row[0]: return "409 Conflict: stale version; reload before updating",409
        if status=="Resolved" and not resolution.strip(): return "422: Resolution notes required",422
        c.execute("UPDATE tickets SET status=%s,inspection=%s,resolution=%s,version=version+1 WHERE id=%s",(status,inspection,resolution,tid))
        log(c,actor,"TICKET_"+status.upper(),"ticket",tid)
    return redirect(url_for("home"))

@app.get("/health")
def health():
    with db() as c: c.execute("SELECT 1")
    return jsonify(status="ok",service="smart-campus",instance=os.getenv("HOSTNAME","local"))

@app.get("/api/bookings")
def api_bookings():
    with db() as c: rows=c.execute("SELECT id,facility_id,requester,status FROM bookings ORDER BY created_at DESC").fetchall()
    return jsonify([{"id":r[0],"facility_id":r[1],"requester":r[2],"status":r[3]} for r in rows])

if __name__=="__main__": app.run(host="0.0.0.0",port=5000)
