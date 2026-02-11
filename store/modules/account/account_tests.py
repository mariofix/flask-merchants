from app.modules.account.controller import AccountController


def test_index():
    account_controller = AccountController()
    result = account_controller.index()
    assert result == {"message": "Hello, World!"}
