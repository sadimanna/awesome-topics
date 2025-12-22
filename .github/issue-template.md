---
title: "DBLP Update · {{ date | date('YYYY-MM-DD') }}"
labels: ["papers", "automation", "dblp"]
---

## 📚 New Papers Detected

The following updates were automatically detected by the scheduled DBLP watcher.

- **Repository**: {{ github.repository }}
- **Trigger**: {{ github.event_name }}
- **Run ID**: {{ github.run_id }}
- **Timestamp**: {{ date | date('YYYY-MM-DD HH:mm:ss') }} UTC

> 🔍 **Summary**: {{ env.TOPIC_COUNT }} topics updated

---

<details open>
<summary><strong>📄 Paper List</strong></summary>

{% if env.MSG %}
{{ env.MSG | safe }}
{% else %}
_No new papers were detected in this run._
{% endif %}

</details>

---

<details>
<summary><strong>ℹ️ Automation Details</strong></summary>

- Workflow: `{{ github.workflow }}`
- Branch: `{{ github.ref }}`
- Actor: `{{ github.actor }}`
- Commit: `{{ github.sha }}`

</details>
