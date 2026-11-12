
from database import db
from werkzeug.security import generate_password_hash
from getpass import getpass

def recover_admin():
    db.init_db()
    conn = db.get_connection()

    try:
        users = conn.execute(
            "SELECT id, username, email, is_admin "
            "FROM users ORDER BY id"
        ).fetchall()

        if not users:
            print("\nNo existing users found.")
            print("Create your first admin account.")

            username = input("New username: ").strip()
            email = input("Email: ").strip()
            password = getpass("New password: ")
            confirm = getpass("Confirm password: ")

            if not username or not email or not password:
                print("All fields are required.")
                return

            if password != confirm:
                print("Passwords do not match.")
                return

            conn.execute(
                """INSERT INTO users
                (username, email, password_hash, is_admin, created_at)
                VALUES (?, ?, ?, 1, ?)""",
                (
                    username,
                    email,
                    generate_password_hash(password),
                    __import__("datetime").datetime.utcnow().isoformat()
                )
            )
            conn.commit()
            print("Admin account created successfully!")
            return

        print("\nExisting accounts:")
        for number, user in enumerate(users, start=1):
            status = "Admin" if user["is_admin"] else "User"
            print(
                f'{number}. Username: {user["username"]} | '
                f'Email: {user["email"]} | Role: {status}'
            )

        choice = input(
            "\nEnter the number of YOUR account: "
        ).strip()

        if not choice.isdigit():
            print("Invalid selection.")
            return

        index = int(choice) - 1

        if index < 0 or index >= len(users):
            print("Invalid selection.")
            return

        selected = users[index]
        print(f'\nSelected account: {selected["username"]}')

        confirm_account = input(
            "Is this your account? Type YES to continue: "
        ).strip()

        if confirm_account != "YES":
            print("Recovery cancelled.")
            return

        password = getpass("Enter your new password: ")
        confirm = getpass("Confirm new password: ")

        if len(password) < 12:
            print("Use a password of at least 12 characters.")
            return

        if password != confirm:
            print("Passwords do not match.")
            return

        conn.execute(
            """UPDATE users
            SET is_admin = 1, password_hash = ?
            WHERE id = ?""",
            (generate_password_hash(password), selected["id"])
        )
        conn.commit()

        print("\nAdmin recovery successful!")
        print("Username:", selected["username"])
        print("Role: Admin")
        print("Now log in using your new password.")

    except Exception as error:
        conn.rollback()
        print("Recovery failed:", error)

    finally:
        conn.close()


if __name__ == "__main__":
    recover_admin()
