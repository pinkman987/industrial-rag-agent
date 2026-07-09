# GitHub发布检查清单

## 1. 敏感信息检查

发布前逐项确认：

- [ ] `.env` 没有提交。
- [ ] `.venv` 没有提交。
- [ ] `data/chroma` 没有提交。
- [ ] `data/uploads` 没有提交。
- [ ] `data/chroma_old` 没有提交。
- [ ] 真实 API Key 没有出现在 README、docs、代码、测试中。
- [ ] `.env.example` 只包含占位符。
- [ ] MySQL 真实密码没有出现在公开文档中。

建议在发布前使用编辑器或命令行搜索 API Key、数据库密码、私有 token 等敏感关键词。搜索范围应覆盖 README、docs、app、tests、scripts 和 frontend，但不应把 `.env` 的真实内容复制到公开文档中。

注意：`.env` 是本地真实配置文件，不应提交到 GitHub；检查公开文件时不要把 `.env` 内容复制到文档或提交记录中。

## 2. 项目文件检查

发布前确认：

- [ ] `README.md` 完整，包含项目简介、启动方式、核心接口和演示说明。
- [ ] `requirements.txt` 完整，包含后端和 Streamlit 前端依赖。
- [ ] `frontend/README.md` 存在。
- [ ] `docs` 文档完整，包括阶段验收、项目架构、演示指南、面试笔记和简历描述。
- [ ] `tests` 可运行。
- [ ] `data/sample_docs` 样例文档存在。
- [ ] 没有 Word 临时文件，例如 `~$*.docx`。
- [ ] 没有 `__pycache__` 被提交。
- [ ] 没有 `*.pyc` 被提交。
- [ ] 没有 `*.log` 被提交。

建议保留的关键文档：

- `docs/stage1_acceptance.md`
- `docs/stage2_acceptance.md`
- `docs/stage3_acceptance.md`
- `docs/stage4_acceptance.md`
- `docs/project_architecture.md`
- `docs/demo_guide.md`
- `docs/interview_notes.md`
- `docs/resume_description.md`
- `docs/final_project_summary.md`

## 3. 功能检查

发布前建议在本地跑一遍核心功能：

- [ ] FastAPI 能启动。
- [ ] Swagger 能访问。
- [ ] Streamlit 能启动。
- [ ] RAG 问答可用。
- [ ] FunctionCalling 问答可用。
- [ ] 故障诊断可用。
- [ ] 诊断报告生成可用。
- [ ] 诊断报告历史查询可用。
- [ ] 设备数据查询可用。

推荐命令：

```powershell
python -m unittest discover
python -m compileall app scripts tests frontend
uvicorn app.main:app --reload
python -m streamlit run frontend/streamlit_app.py
```

## 4. Git检查命令

提交前运行：

```powershell
git status
git log --oneline
git check-ignore .env
git check-ignore .venv
git check-ignore data/chroma
git check-ignore data/uploads
```

期望结果：

- `git status` 只显示准备提交的源码、文档、测试和样例文件。
- `git log --oneline` 能看到清晰的提交历史。
- `git check-ignore` 对 `.env`、`.venv`、`data/chroma`、`data/uploads` 返回对应路径，说明这些内容会被 Git 忽略。

如果 `git check-ignore` 没有输出，需要先检查 `.gitignore` 是否包含对应规则。

## 5. 建议提交前最终核对

- [ ] README 中没有真实 API Key。
- [ ] docs 中没有真实 API Key。
- [ ] `.env.example` 使用 `your_xxx` 这类占位符。
- [ ] `.env` 没有出现在 `git status` 中。
- [ ] `data/chroma` 和 `data/uploads` 没有出现在 `git status` 中。
- [ ] 提交信息能概括本次变更，例如“add github demo guide and final project summary”。
