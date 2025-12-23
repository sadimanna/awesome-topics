---
title: "DBLP Update · {{ date | date('YYYY-MM-DD') }}"
labels: ["papers", "automation", "dblp"]
---

## 📚 New Papers Detected

---

<details open>
<summary><strong>📄 Paper List</strong></summary>

{% if env.MSG %}
{{ env.MSG | safe }}
{% else %}
_No new papers were detected in this run._
{% endif %}

</details>

> Check [awesome-topics](https://sadimanna.github.io/awesome-topics/) for the full list.
---