"C:\Program Files\Git\cmd\git.exe" init
"C:\Program Files\Git\cmd\git.exe" add .
"C:\Program Files\Git\cmd\git.exe" config user.email "admin@biet.gov"
"C:\Program Files\Git\cmd\git.exe" config user.name "BIET Admin"
"C:\Program Files\Git\cmd\git.exe" commit -m "Initial commit of Election System"
"C:\Program Files\Git\cmd\git.exe" branch -M main
"C:\Program Files\Git\cmd\git.exe" remote add origin https://github.com/developerakashp/onlinevotingsystem.git
"C:\Program Files\Git\cmd\git.exe" push -u origin main
