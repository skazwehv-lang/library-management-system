from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
import os
import shutil
from datetime import datetime
import webbrowser
import threading

app = Flask(__name__)
app.secret_key = "library-secret-key-2026"

DATABASE = "library.db"
BACKUP_FOLDER = "backups"
def backup_database():

    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)

    date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    backup_file = os.path.join(
        BACKUP_FOLDER,
        f"library_backup_{date_time}.db"
    )

    shutil.copy2(DATABASE, backup_file)

    return backup_file


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admission_number TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            gender TEXT,
            class_name TEXT,
            stream TEXT,
            phone TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn TEXT,
            title TEXT NOT NULL,
            author TEXT,
            subject TEXT,
            category TEXT,
            quantity INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()
def fix_books_table():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS books_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn TEXT,
            title TEXT NOT NULL,
            author TEXT,
            subject TEXT,
            category TEXT,
            quantity INTEGER DEFAULT 1
        )
    """)

    conn.execute("""
        INSERT INTO books_new
        (id, isbn, title, author, subject, category, quantity)
        SELECT id, isbn, title, author, subject, category, quantity
        FROM books
    """)

    conn.execute("DROP TABLE books")

    conn.execute("ALTER TABLE books_new RENAME TO books")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS borrowings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            borrow_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT DEFAULT 'Borrowed',
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    """)

    conn.commit()
    conn.close()


create_tables()
fix_books_table()


@app.route("/")
def home():
    return redirect("/login")
@app.route("/students")
def students():
    if not session.get("logged_in"):
        return redirect("/login")

    search = request.args.get("q", "")

    conn = get_db()

    if search:

        students = conn.execute("""
            SELECT * FROM students
            WHERE admission_number LIKE ?
            OR full_name LIKE ?
            OR class_name LIKE ?
            ORDER BY full_name
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        )).fetchall()

    else:

        students = conn.execute("""
            SELECT * FROM students
            ORDER BY full_name
        """).fetchall()


    conn.close()

    return render_template(
        "students.html",
        students=students
    )
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["logged_in"] = True
            session["username"] = username

            return redirect("/dashboard")

        else:

            return "Invalid username or password."

    return render_template("login.html")
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")
@app.route("/backup")
def backup():

    if not session.get("logged_in"):
        return redirect("/login")

    backup_file = backup_database()

    flash("Database backup created successfully.")

    return redirect("/dashboard")
@app.route("/add-student", methods=["GET", "POST"])
def add_student():

    if request.method == "POST":

        admission_number = request.form["admission_number"]
        full_name = request.form["full_name"]
        gender = request.form["gender"]
        class_name = request.form["class_name"]
        stream = request.form["stream"]
        phone = request.form["phone"]

        conn = get_db()

        existing_student = conn.execute("""
            SELECT id
            FROM students
            WHERE admission_number = ?
        """, (admission_number,)).fetchone()

        if existing_student:
            conn.close()
            return "Admission number already exists."

        conn.execute("""
            INSERT INTO students
            (admission_number, full_name, gender, class_name, stream, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            admission_number,
            full_name,
            gender,
            class_name,
            stream,
            phone
        ))

        conn.commit()
        conn.close()

        return redirect("/students")

    return render_template("add_student.html")
@app.route("/add-book", methods=["GET", "POST"])
def add_book():

    if request.method == "POST":

        isbn = request.form["isbn"]
        title = request.form["title"]
        author = request.form["author"]
        subject = request.form["subject"]
        category = request.form["category"]
        quantity = int(request.form["quantity"])

        if quantity < 1:
            return "Quantity must be at least 1."

        conn = get_db()

        conn.execute("""
            INSERT INTO books
            (isbn, title, author, subject, category, quantity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            isbn,
            title,
            author,
            subject,
            category,
            quantity
        ))

        conn.commit()
        conn.close()

        return redirect("/books")

    return render_template("add_book.html")
@app.route("/view-student/<int:student_id>")
def view_student(student_id):

    conn = get_db()

    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    conn.close()

    return render_template(
        "view_student.html",
        student=student
    )
@app.route("/edit-student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):

    conn = get_db()

    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    if request.method == "POST":

        admission_number = request.form["admission_number"]
        full_name = request.form["full_name"]
        gender = request.form["gender"]
        class_name = request.form["class_name"]
        stream = request.form["stream"]
        phone = request.form["phone"]

        conn.execute("""
            UPDATE students

            SET admission_number = ?,
                full_name = ?,
                gender = ?,
                class_name = ?,
                stream = ?,
                phone = ?

            WHERE id = ?
        """, (
            admission_number,
            full_name,
            gender,
            class_name,
            stream,
            phone,
            student_id
        ))

        conn.commit()
        conn.close()

        return redirect("/students")

    conn.close()

    return render_template(
        "edit_student.html",
        student=student
    )
@app.route("/books")
def books():
    if not session.get("logged_in"):
        return redirect("/login")

    search = request.args.get("q", "")

    conn = get_db()

    if search:

        books = conn.execute("""
            SELECT * FROM books
            WHERE title LIKE ?
            OR author LIKE ?
            OR isbn LIKE ?
            OR subject LIKE ?
            ORDER BY title
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        )).fetchall()

    else:

        books = conn.execute("""
            SELECT * FROM books
            ORDER BY title
        """).fetchall()

    conn.close()

    return render_template(
        "books.html",
        books=books
    )
@app.route("/view-book/<int:book_id>")
def view_book(book_id):

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    conn.close()

    return render_template(
        "view_book.html",
        book=book
    )
@app.route("/edit-book/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):

    conn = get_db()

    if request.method == "POST":

        isbn = request.form["isbn"]
        title = request.form["title"]
        author = request.form["author"]
        subject = request.form["subject"]
        category = request.form["category"]
        quantity = request.form["quantity"]

        conn.execute("""
            UPDATE books
            SET isbn = ?,
                title = ?,
                author = ?,
                subject = ?,
                category = ?,
                quantity = ?
            WHERE id = ?
        """, (
            isbn,
            title,
            author,
            subject,
            category,
            quantity,
            book_id
        ))

        conn.commit()
        conn.close()

        return redirect("/books")

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    conn.close()

    return render_template(
        "edit_book.html",
        book=book
    )
@app.route("/delete-book/<int:book_id>")
def delete_book(book_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM books WHERE id = ?",
        (book_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/books")
@app.route("/borrow-book", methods=["GET", "POST"])
def borrow_book():
    if not session.get("logged_in"):
            return redirect("/login")

    conn = get_db()

    if request.method == "POST":

        student_id = request.form["student_id"]
        book_id = request.form["book_id"]
        borrow_date = request.form["borrow_date"]

        book = conn.execute(
            "SELECT * FROM books WHERE id = ?",
            (book_id,)
        ).fetchone()

        if book["quantity"] <= 0:

            conn.close()

            return "This book is currently out of stock."

        conn.execute("""
            INSERT INTO borrowings
            (student_id, book_id, borrow_date)
            VALUES (?, ?, ?)
        """, (
            student_id,
            book_id,
            borrow_date
        ))

        conn.execute("""
            UPDATE books
            SET quantity = quantity - 1
            WHERE id = ?
        """, (book_id,))

        conn.commit()
        conn.close()

        return redirect("/books")

    students = conn.execute("""
        SELECT *
        FROM students
        ORDER BY full_name
    """).fetchall()

    books = conn.execute("""
        SELECT *
        FROM books
        WHERE quantity > 0
        ORDER BY title
    """).fetchall()

    conn.close()

    return render_template(
        "borrow_book.html",
        students=students,
        books=books
    )
@app.route("/return-books")
def return_books():
    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()

    borrowings = conn.execute("""
        SELECT
            borrowings.id,
            students.full_name,
            students.admission_number,
            books.title,
            borrowings.borrow_date,
            borrowings.status
        FROM borrowings
        JOIN students
            ON borrowings.student_id = students.id
        JOIN books
            ON borrowings.book_id = books.id
        WHERE borrowings.status = 'Borrowed'
        ORDER BY borrowings.borrow_date DESC
    """).fetchall()

    conn.close()

    return render_template(
        "return_book.html",
        borrowings=borrowings
    )
@app.route("/return-book/<int:borrowing_id>")
def return_book(borrowing_id):

    conn = get_db()

    borrowing = conn.execute("""
        SELECT *
        FROM borrowings
        WHERE id = ?
    """, (borrowing_id,)).fetchone()

    if borrowing is None:
        conn.close()
        return "Borrowing record not found."

    if borrowing["status"] == "Returned":
        conn.close()
        return "This book has already been returned."

    conn.execute("""
        UPDATE borrowings
        SET status = 'Returned',
            return_date = DATE('now')
        WHERE id = ?
    """, (borrowing_id,))

    conn.execute("""
        UPDATE books
        SET quantity = quantity + 1
        WHERE id = ?
    """, (borrowing["book_id"],))

    conn.commit()
    conn.close()

    return redirect("/return-books")
@app.route("/borrowing-history")
def borrowing_history():
    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()

    borrowings = conn.execute("""
        SELECT
            borrowings.id,
            students.full_name,
            students.admission_number,
            books.title,
            borrowings.borrow_date,
            borrowings.return_date,
            borrowings.status
        FROM borrowings
        JOIN students
            ON borrowings.student_id = students.id
        JOIN books
            ON borrowings.book_id = books.id
        ORDER BY borrowings.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "borrowing_history.html",
        borrowings=borrowings
    )
@app.route("/dashboard")
def dashboard():

    if not session.get("logged_in"):
        return redirect("/login")

    conn = get_db()

    total_students = conn.execute("""
        SELECT COUNT(*) AS total
        FROM students
    """).fetchone()["total"]

    total_books = conn.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM books
    """).fetchone()["total"]

    borrowed_books = conn.execute("""
        SELECT COUNT(*) AS total
        FROM borrowings
        WHERE status = 'Borrowed'
    """).fetchone()["total"]

    available_books = total_books - borrowed_books

    conn.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_books=total_books,
        borrowed_books=borrowed_books,
        available_books=available_books
    )

    students = conn.execute("""
        SELECT *
        FROM students
        ORDER BY full_name
    """).fetchall()

    books = conn.execute("""
        SELECT *
        FROM books
        WHERE quantity > 0
        ORDER BY title
    """).fetchall()

    conn.close()

    return render_template(
        "borrow_book.html",
        students=students,
        books=books
    )
@app.route("/delete-student/<int:student_id>")
def delete_student(student_id):

    conn = get_db()

    conn.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/students")

if __name__ == "__main__":
    app.run(debug=False)