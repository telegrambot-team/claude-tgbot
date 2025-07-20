from database.models import User


def test_user_str():
    user = User(id=1, fullname="John Doe")
    assert str(user) == "User(id: 1, fullname: John Doe)"
