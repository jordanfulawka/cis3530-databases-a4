# cis3530-databases-a4

#setting things up on windows powershell
python3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

createdb -U postgres my_company_db or if that doesnt work, try psql -U username -c "CREATE DATABASE my_company_db;"
$env:DATABASE_URL="postgresql://username:password@localhost/my_company_db"

psql postgresql://user:password@localhost/my_company_db -f company_v3.02.sql
psql postgresql://user:password@localhost/my_company_db -f team_setup.sql

Creating admin and viewer:
python create_user.py admin
python create_user.py viewer

flask run
