"""FoxHire MCP Server — exposes the FoxHire.AI job search pipeline as MCP tools."""

from mcp.server.fastmcp import FastMCP
from foxhire_client import FoxHireClient, FoxHireError

mcp = FastMCP("FoxHire")
client = FoxHireClient()


@mcp.tool()
async def list_jobs() -> str:
    """List all jobs in your FoxHire pipeline with their current status.
    Returns job IDs, titles, companies, and pipeline status.
    """
    try:
        jobs = await client.list_jobs()
    except FoxHireError as e:
        return f"Error: {e}"

    if not jobs:
        return "No jobs in your pipeline yet."

    lines = []
    for i, job in enumerate(jobs, 1):
        contacts = job.get("contacts", [])
        line = (
            f"{i}. [ID: {job['id']}] {job.get('title', 'Untitled')} "
            f"at {job.get('company', 'Unknown')}\n"
            f"   Status: {job.get('status', 'New')}"
        )
        if job.get("location"):
            line += f" | Location: {job['location']}"
        if job.get("remote_status"):
            line += f" ({job['remote_status']})"
        line += f"\n   Contacts: {len(contacts)}"
        lines.append(line)

    return f"Found {len(jobs)} jobs:\n\n" + "\n\n".join(lines)


@mcp.tool()
async def parse_job_posting(text: str = "", url: str = "") -> str:
    """Parse a job posting to extract structured data and save it to your pipeline.
    Provide either the full text of a job posting OR a URL to one.
    Returns the saved job with company, title, requirements, and a job ID
    you can use with discover_contacts.
    """
    if not text and not url:
        return "Error: provide either 'text' (raw posting) or 'url' (link to posting)."

    try:
        if url and not text:
            job = await client.parse_job_url(url)
        else:
            job = await client.parse_job(text, url if url else None)
    except FoxHireError as e:
        return f"Error: {e}"

    parts = [
        f"Job saved! ID: {job.get('id')}",
        f"Title: {job.get('title', 'N/A')}",
        f"Company: {job.get('company', 'N/A')}",
        f"Status: {job.get('status', 'New')}",
    ]
    for field in [
        "location",
        "remote_status",
        "seniority_level",
        "department",
        "estimated_company_size",
        "hiring_manager_persona",
    ]:
        if job.get(field):
            parts.append(f"{field.replace('_', ' ').title()}: {job[field]}")
    if job.get("key_requirements"):
        parts.append(f"Key Requirements: {', '.join(job['key_requirements'][:5])}")
    if job.get("relevant_skills"):
        parts.append(f"Relevant Skills: {', '.join(job['relevant_skills'][:5])}")

    parts.append(f"\nNext step: use discover_contacts with job_id={job.get('id')}")
    return "\n".join(parts)


@mcp.tool()
async def discover_contacts(job_id: int) -> str:
    """Discover hiring decision makers for a parsed job using AI web search.
    Finds likely hiring managers with confidence levels and LinkedIn profiles.
    Requires a job_id from parse_job_posting or list_jobs.
    Costs 1 credit.
    """
    try:
        result = await client.discover_contacts(job_id)
    except FoxHireError as e:
        return f"Error: {e}"

    contacts = result.get("contacts", [])
    credits = result.get("credits", "?")

    if not contacts:
        return f"No contacts discovered. Credits remaining: {credits}"

    lines = []
    for c in contacts:
        suggested = " ★ SUGGESTED FIRST CONTACT" if c.get("is_suggested_first_contact") else ""
        line = (
            f"[ID: {c['id']}] {c.get('name', 'Unknown')} — "
            f"{c.get('title', 'N/A')} "
            f"(Confidence: {c.get('confidence_level', 'N/A')}){suggested}"
        )
        if c.get("linkedin_url"):
            line += f"\n  LinkedIn: {c['linkedin_url']}"
        if c.get("confidence_reasoning"):
            line += f"\n  Why: {c['confidence_reasoning']}"
        if c.get("suggested_reason"):
            line += f"\n  Suggested because: {c['suggested_reason']}"
        lines.append(line)

    header = f"Found {len(contacts)} contacts (Credits remaining: {credits}):\n"
    return header + "\n\n".join(lines)


@mcp.tool()
async def research_contact(contact_id: int) -> str:
    """Deep-research a contact using AI web search. Returns a personalization
    brief with key findings, outreach angles, and sources.
    Requires a contact_id from discover_contacts.
    Costs 1 credit.
    """
    try:
        result = await client.research_contact(contact_id)
    except FoxHireError as e:
        return f"Error: {e}"

    contact = result.get("contact", {})
    credits = result.get("credits", "?")
    brief = contact.get("research_brief") or {}
    parts = []

    if brief.get("key_findings"):
        parts.append("KEY FINDINGS:")
        for f in brief["key_findings"]:
            parts.append(f"  - {f}")

    if brief.get("shared_background"):
        bg = brief["shared_background"]
        if isinstance(bg, list):
            parts.append("\nSHARED BACKGROUND:")
            for item in bg:
                parts.append(f"  - {item}")
        else:
            parts.append(f"\nSHARED BACKGROUND: {bg}")

    if brief.get("outreach_angles"):
        parts.append("\nOUTREACH ANGLES:")
        for angle in brief["outreach_angles"]:
            name = angle.get("name") or angle.get("title", "Untitled")
            desc = angle.get("description", "")
            angle_type = angle.get("type", "")
            text = f"  [{name}]"
            if angle_type:
                text += f" ({angle_type})"
            if desc:
                text += f"\n    {desc}"
            parts.append(text)

    if brief.get("source_urls"):
        parts.append("\nSOURCES:")
        for src in brief["source_urls"]:
            parts.append(f"  - {src}")

    parts.append(f"\nCredits remaining: {credits}")

    if not parts:
        return f"Research complete but no structured brief returned.\nRaw: {brief}\nCredits remaining: {credits}"
    return "\n".join(parts)


@mcp.tool()
async def draft_outreach_email(
    contact_id: int, selected_angles: str = ""
) -> str:
    """Draft a personalized cold outreach email for a researched contact.
    Optionally specify outreach angle names (comma-separated) from the
    research brief. Contact must be researched first.
    Costs 0 credits.
    """
    angles = []
    if selected_angles:
        angles = [{"name": a.strip(), "description": ""} for a in selected_angles.split(",")]

    try:
        result = await client.draft_email(contact_id, selected_angles=angles)
    except FoxHireError as e:
        return f"Error: {e}"

    parts = []
    if result.get("subject"):
        parts.append(f"SUBJECT: {result['subject']}")
    if result.get("body"):
        parts.append(f"\n{result['body']}")
    return "\n".join(parts) if parts else str(result)


if __name__ == "__main__":
    mcp.run()
