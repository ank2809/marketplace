from __future__ import absolute_import
import requests
import os
from flask.ext.mongoengine import MongoEngine
from flask.ext.mongoengine.wtf import model_form
from werkzeug import secure_filename
from wtforms import PasswordField
from flask.ext.login import LoginManager, login_user, logout_user,\
login_required, current_user
from flask import Flask, render_template, redirect, request, url_for,\
send_from_directory
from flask_mail import Mail
from flask_mail import Message


app = Flask(__name__)
app.config["DEBUG"] = True
app.config['MONGODB_SETTINGS'] = {'db': 'books'}
app.config['SECRET_KEY'] = 'secretkey'
app.config['WTF_CSRF_ENABLED'] = True
db = MongoEngine(app)

from .models.user import User
from .models.book import Book

login_manager = LoginManager()
login_manager.init_app(app)

UserForm = model_form(User)
UserForm.password = PasswordField('password')

BookForm = model_form(Book)
mail = Mail(app)


@login_manager.user_loader
def load_user(name):
    users = User.objects(name=name)
    if len(users) != 0:
        return users[0]
    else:
        return None


@app.route("/", methods=['GET', 'POST'])
def home():
    form = UserForm(request.form)

    if request.method == 'POST' and form.validate():

        if request.form["form"] == "Login":
            user = User.objects(name=form.name.data, password=form
                                .password.data).first()
            if user:
                login_user(user)
                return redirect('/booklist')

        else:
            if load_user(form.name.data) is None:
                form.save()
                return redirect('/')

    return render_template('login.html', form=form)



@app.route("/booklist", methods=["POST", "GET"])
@login_required
def getBooks():
    if request.method == "POST":
        id = request.form["search"]
        return redirect("/booklist/" + id)
    else:
        listOfBooks = Book.objects()
        return render_template("booklist.html", listOfBooks=listOfBooks)


@app.route("/sell/", methods=["POST", "GET"])
def sell():
    form = BookForm(request.form)

    if form.validate():

        # Get Google API Information for book name
        url = "https://www.googleapis.com/books/v1/volumes?q="\
            + form.book_name.data.replace(" ", "%20")
        response_dict = requests.get(url).json()

        # Search through list of books until one has a valid description
        # and image link
        bookNumber = 0
        while "description" not in response_dict["items"][bookNumber]["volumeInfo"]\
        or "imageLinks" not in response_dict["items"][bookNumber]["volumeInfo"]:
            bookNumber += 1
        # Assign description and image link from Google API, assign user name
        # and contact info from current user
        # Truncate to 500 characters
        description = response_dict["items"][bookNumber]["volumeInfo"]["description"]
        if len(description) > 500:
            description = "{}...".format(description[:501])

        image = response_dict["items"][bookNumber]["volumeInfo"]\
        ["imageLinks"]["thumbnail"]

        form.user_name.data = current_user.name
        form.contact_info.data = current_user.contact_info

        # Assign and save book
        book = Book(user_name=form.user_name.data, book_name=form.book_name.
                    data, price=form.price.data,
                    contact_info=form.contact_info.data,
                    description=description, image=image)
        book.save()

        return redirect('/booklist')
    else:
        return render_template("sell.html", form=form)

@app.route("/sendEmail")
@login_required
def sendEmail():
    msg = Message("Hello", sender="ibarrac27@gmail.com",recipients=["cfi2103@columbia.edu"])
    mail.send(msg)

@app.route("/bookinfo/<id>")
def bookinfo(id):
    books = Book.objects(book_name=id)
    return render_template("bookinfo.html", book=books[0])


@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")


@app.route("/booklist/<id>", methods=["POST", "GET"])
@login_required
def search(id):
    if request.method == "POST":
        id = request.form["search"]
        return redirect("/booklist/" + id)

    else:
        listOfBooks = Book.objects()
        items = []
        for book in listOfBooks:
                if(id.lower() in book.book_name.lower()):
                        items.append(book)
        for book in listOfBooks:
                if book not in items and\
                   id.lower() in book.description.lower():
                        items.append(book)

        return render_template("booklist.html", listOfBooks=items)


@app.route("/myBooks/", methods=["POST", "GET"])
@login_required
def myBooks():
    list_of_my_books = Book.objects(user_name=current_user.name)
    return render_template("myBooks.html", list_of_my_books=list_of_my_books)


@app.route("/delete/<id>")
@login_required
def delete(id):
    deleted_book = Book.objects(book_name=id)[0].book_name
    Book.objects(book_name=id).delete()
    return render_template("delete.html", deleted_book=deleted_book)

"""
for text in Book.objects():
    text.delete()
for guy in User.objects():
    guy.delete()
"""

app.run(debug=True)