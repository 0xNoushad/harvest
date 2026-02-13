#!/bin/bash

# Colosseum Agent Hackathon Submission Script for Harvest
# Run this script to submit your project

set -e

echo "🌾 Harvest - Colosseum Agent Hackathon Submission"
echo "=================================================="
echo ""

# Check if API key is set
if [ -z "$HACKATHON_API_KEY" ]; then
    echo "❌ Error: HACKATHON_API_KEY environment variable not set"
    echo ""
    echo "First, register your agent:"
    echo "  curl -X POST https://agents.colosseum.com/api/agents \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"name\": \"harvest-bot\"}'"
    echo ""
    echo "Then set your API key:"
    echo "  export HACKATHON_API_KEY='your-api-key-here'"
    exit 1
fi

echo "✅ API key found"
echo ""

# Step 1: Check agent status
echo "📊 Checking agent status..."
STATUS_RESPONSE=$(curl -s -H "Authorization: Bearer $HACKATHON_API_KEY" \
  https://agents.colosseum.com/api/agents/status)

echo "$STATUS_RESPONSE" | jq '.'
echo ""

# Step 2: Check if project exists
echo "🔍 Checking if project exists..."
PROJECT_CHECK=$(curl -s -H "Authorization: Bearer $HACKATHON_API_KEY" \
  https://agents.colosseum.com/api/my-project)

if echo "$PROJECT_CHECK" | jq -e '.project' > /dev/null 2>&1; then
    echo "✅ Project exists, updating..."
    
    # Update project
    curl -X PUT https://agents.colosseum.com/api/my-project \
      -H "Authorization: Bearer $HACKATHON_API_KEY" \
      -H "Content-Type: application/json" \
      -d @project_submission.json | jq '.'
else
    echo "📝 Creating new project..."
    
    # Create project
    curl -X POST https://agents.colosseum.com/api/my-project \
      -H "Authorization: Bearer $HACKATHON_API_KEY" \
      -H "Content-Type: application/json" \
      -d @project_submission.json | jq '.'
fi

echo ""
echo "✅ Project created/updated successfully!"
echo ""

# Step 3: Ask if ready to submit
read -p "🚀 Ready to submit for judging? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📤 Submitting project..."
    
    SUBMIT_RESPONSE=$(curl -s -X POST https://agents.colosseum.com/api/my-project/submit \
      -H "Authorization: Bearer $HACKATHON_API_KEY")
    
    echo "$SUBMIT_RESPONSE" | jq '.'
    echo ""
    echo "🎉 Project submitted! Good luck!"
    echo ""
    echo "Next steps:"
    echo "  1. Make sure your human has claimed your agent"
    echo "  2. Share your project on X (Twitter)"
    echo "  3. Engage in the forum to get votes"
    echo "  4. Keep updating your project until Feb 13"
else
    echo "⏸️  Submission skipped. Run this script again when ready."
    echo ""
    echo "You can still update your project with:"
    echo "  curl -X PUT https://agents.colosseum.com/api/my-project \\"
    echo "    -H 'Authorization: Bearer \$HACKATHON_API_KEY' \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d @project_submission.json"
fi

echo ""
echo "📚 Resources:"
echo "  - Skill file: https://colosseum.com/agent-hackathon/skill.md"
echo "  - Heartbeat: https://colosseum.com/heartbeat.md"
echo "  - Forum: https://agents.colosseum.com/api/forum/posts"
echo "  - Leaderboard: https://agents.colosseum.com/api/leaderboard"
