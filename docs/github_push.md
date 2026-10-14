# GitHub への push 手順（久しぶりの人向け）

Windows で、この `tutorial_github` フォルダを新しい GitHub リポジトリとして公開（push）するまでの手順です。

---

## 0. 事前準備（初回だけ）

### Git が入っているか確認
PowerShell（またはコマンドプロンプト）で:
```powershell
git --version
```
バージョンが表示されなければ <https://git-scm.com/download/win> からインストールします（設定はすべて既定のままで OK）。

### 名前とメールを設定
```powershell
git config --global user.name  "Haruki Matsui"
git config --global user.email "GitHubに登録したメールアドレス"
git config --global core.quotepath false     # 日本語ファイル名を文字化けさせない
git config --global init.defaultBranch main  # 最初のブランチ名を main にする
```
`git config --global --list` で確認できます。

### GitHub へのログイン方法
今は **パスワードでの push はできません**。次のどちらかを使います。

- **おすすめ：Git Credential Manager（Git for Windows に同梱）**
  初めて push したときにブラウザが開くので、GitHub にログインして許可するだけです。
- **GitHub CLI を使う場合**
  ```powershell
  winget install GitHub.cli
  gh auth login        # GitHub.com → HTTPS → ブラウザでログイン を選ぶ
  ```

---

## 1. GitHub 上で空のリポジトリを作る

1. <https://github.com> にログイン → 右上の **「+」→「New repository」**
2. **Repository name**：例 `virtual-city-flood-tutorial`
3. **Private / Public** を選ぶ（研究室内部のデータを含むので、まずは **Private** を推奨）
4. **「Add a README file」「.gitignore」「license」は全部チェックしない**（こちらで用意済みのため。付けると最初の push で衝突します）
5. **Create repository** を押す → 表示される URL（`https://github.com/ユーザー名/virtual-city-flood-tutorial.git`）をコピー

---

## 2. ローカルでリポジトリを作って push する

```powershell
# フォルダに移動
cd C:\Users\matsu\Documents\Claude\tutorial\tutorial_github

# Git 管理を開始
git init

# 追加されるファイルを確認（.gitignore で除外されたものは出てこない）
git status

# すべてステージ → コミット
git add .
git commit -m "初回コミット：仮想都市 氾濫解析 入力データ作成チュートリアル"

# GitHub のリポジトリを登録（URL は手順 1 でコピーしたもの）
git remote add origin https://github.com/ユーザー名/virtual-city-flood-tutorial.git

# push（初回だけ -u を付ける）
git push -u origin main
```

ブラウザでリポジトリのページを開き、ファイルと README が表示されていれば完了です。

> **改行コードの警告**（`LF will be replaced by CRLF` など）が出ても問題ありません。

---

## 3. 2 回目以降の更新

```powershell
cd C:\Users\matsu\Documents\Claude\tutorial\tutorial_github
git status                       # 何が変わったか確認
git add .                        # または git add 07_river/README.md のように個別に
git commit -m "07_river の手順を追記"
git push
```

他の人（や別の PC）が更新した内容を取り込むとき:
```powershell
git pull
```

別の PC で最初に取得するとき:
```powershell
git clone https://github.com/ユーザー名/virtual-city-flood-tutorial.git
```

---

## 4. よくあるトラブル

| 症状 | 原因と対処 |
|---|---|
| `remote origin already exists` | すでに登録済み。`git remote set-url origin <URL>` で付け替える |
| `failed to push some refs ... (fetch first)` | GitHub 側に README などが先にある。`git pull --rebase origin main` してから `git push` |
| `src refspec main does not match any` | まだコミットしていない、またはブランチ名が `master`。`git branch -M main` してから push |
| `Authentication failed` / パスワードを聞かれる | パスワードは使えない。Credential Manager のブラウザログイン、または `gh auth login` を使う |
| `File ... is 100.00 MB; this exceeds GitHub's file size limit` | 1 ファイル 100 MB が上限。`.gitignore` に追加し、`git rm --cached <ファイル>` してからコミットし直す |
| 間違えて巨大ファイルや個人情報をコミットした（push 前） | `git reset --soft HEAD~1` で直前のコミットを取り消し、`.gitignore` を直してやり直す |

---

## 5. このリポジトリで Git 管理から外しているもの（`.gitignore`）

- コンパイル生成物：`*.out`, `*.exe`, `*.obj`, `*.mod`
- 一時ファイル：`*.lck`, `__pycache__/`
- 確認用出力：`check*.dat`
- **研究室資料 `docs/reference/`**（pptx / 卒論 pdf など）
  → Private リポジトリで共有してよい場合は、`.gitignore` の `docs/reference/` の行を消してから `git add .` してください。

リポジトリ全体は 100 MB 程度（`docs/reference/` を除く）で、1 ファイルの最大は 10 MB（`02_DEM_text/example_output/out5m.txt`）なので、GitHub の制限内に収まっています。

---

## 6. （任意）GitHub Desktop を使う場合

コマンドが苦手なら <https://desktop.github.com> の GitHub Desktop でも同じことができます。

1. **File → Add local repository** で `tutorial_github` フォルダを選ぶ → 「create a repository」を押す
2. 左下にコミットメッセージを書いて **Commit to main**
3. 上部の **Publish repository** → Private にチェック → Publish
