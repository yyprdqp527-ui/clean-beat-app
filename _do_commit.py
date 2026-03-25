import subprocess

result = subprocess.run(
    ['git', 'add', 'templates/base.html', 'templates/tasks.html'],
    cwd='/Users/anne-gaelledaval/Downloads/Appli web-2',
    capture_output=True, text=True
)
print("add:", result.returncode, result.stderr)

msg = "fix: couleur de texte - supprime regle CSS globale destructrice\n\n- Supprime ancienne regle * qui ecrasait inputs et cartes\n- inputs/textarea/select: texte fonce (#153036) meme sur theme sombre\n- .task-card fond blanc: texte propre conserve\n- body herite couleur adaptive pour texte directement sur le fond"

result2 = subprocess.run(
    ['git', 'commit', '-m', msg],
    cwd='/Users/anne-gaelledaval/Downloads/Appli web-2',
    capture_output=True, text=True
)
print("commit:", result2.returncode)
print(result2.stdout)
if result2.stderr: print("STDERR:", result2.stderr)
