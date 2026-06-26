from odoo import http
from odoo.http import request
from werkzeug.wrappers import Response


class BeltTestRosterController(http.Controller):
    @http.route(["/odoo/belt-progression/test-roster", "/belt_test/roster/print"], type="http", auth="user", website=False)
    def belt_test_roster_page(self):
        """Render the belt test roster page with embedded CSS."""
        # Read the CSS file content
        try:
            with open("/mnt/extra-addons/dojo_belt_progression/static/src/css/roster_print.css", "r") as f:
                css_content = f.read()
        except:
            css_content = ""

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>Belt Test Roster</title>
    <style>{css_content}</style>
</head>
<body>
    <div class="belt-test-roster">
        <div class="roster-header">
            <h2>Belt Test Roster</h2>
        </div>
        <div class="roster-list">
            <div class="roster-member">
                <div class="member-info">
                    <div class="member-name">Test Member</div>
                    <div class="member-rank">White Belt</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
        return Response(html, content_type="text/html")
    @http.route("/belt_test/roster/data", type="jsonrpc", auth="user")
    def get_roster_data(self):
        """Return members grouped by class template (program) and current rank."""
        Member = request.env["dojo.member"]
        Template = request.env["dojo.class.template"]
        Rank = request.env["dojo.belt.rank"]

        members = Member.search([("active", "=", True)])
        templates = Template.search([("active", "=", True)], order="name")
        ranks = Rank.search([("active", "=", True)], order="sequence, name")

        member_data = []
        for m in members:
            template_ids = m.env["dojo.class.enrollment"].search(
                [("member_id", "=", m.id), ("status", "=", "registered")]
            ).mapped("session_id.template_id").ids

            member_data.append({
                "id": m.id,
                "name": m.name,
                "current_rank_id": m.current_rank_id.id if m.current_rank_id else False,
                "current_rank_name": m.current_rank_id.name if m.current_rank_id else "No Rank",
                "template_ids": list(set(template_ids)),
            })

        template_data = [{"id": t.id, "name": t.name} for t in templates]
        rank_data = [{"id": r.id, "name": r.name, "sequence": r.sequence} for r in ranks]

        return {
            "members": member_data,
            "templates": template_data,
            "ranks": rank_data,
        }

    @http.route("/belt_test/roster/save", type="jsonrpc", auth="user")
    def save_roster(self, name, test_date, member_ids, template_id=None, rank_id=None):
        """Save a belt test roster as a dojo.belt.test record."""
        BeltTest = request.env["dojo.belt.test"]
        Registration = request.env["dojo.belt.test.registration"]
        Member = request.env["dojo.member"]
        Rank = request.env["dojo.belt.rank"]

        template = request.env["dojo.class.template"].browse(template_id) if template_id else False
        program_id = template.program_id.id if template and template.program_id else False

        belt_test = BeltTest.create({
            "name": name,
            "test_date": test_date,
            "program_id": program_id,
            "state": "scheduled",
        })

        for member_id in member_ids:
            member = Member.browse(member_id)

            # Determine target rank: either the filter rank or next rank after member's current rank
            target_rank_id = None
            if rank_id:
                target_rank_id = rank_id
            elif member.current_rank_id:
                # Find the next rank in sequence
                next_rank = Rank.search([
                    ('sequence', '>', member.current_rank_id.sequence),
                    ('active', '=', True)
                ], order='sequence', limit=1)
                target_rank_id = next_rank.id if next_rank else member.current_rank_id.id
            else:
                # No current rank, use the first rank
                first_rank = Rank.search([('active', '=', True)], order='sequence', limit=1)
                target_rank_id = first_rank.id if first_rank else False

            if target_rank_id:
                Registration.create({
                    "test_id": belt_test.id,
                    "member_id": member_id,
                    "target_rank_id": target_rank_id,
                })

        return {
            "id": belt_test.id,
            "name": belt_test.name,
        }
