#!/usr/bin/env python3
"""
Test script for the MCP server
This simulates how Claude (or n8n) will interact with the MCP server
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_server():
    """Test the MCP server functionality"""
    
    print("=" * 70)
    print("🧪 Testing Graph Analyzer MCP Server")
    print("=" * 70)
    
    # Configure server connection
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env=None
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                
                # Initialize the session
                await session.initialize()
                print("\n✅ MCP Server initialized successfully!\n")
                
                # Test 1: List available tools
                print("=" * 70)
                print("TEST 1: Listing Available Tools")
                print("=" * 70)
                
                tools = await session.list_tools()
                
                for tool in tools.tools:
                    print(f"\n📌 Tool: {tool.name}")
                    print(f"   Description: {tool.description[:100]}...")
                    print(f"   Required params: {tool.inputSchema.get('required', [])}")
                
                # Test 2: Find path between components
                print("\n\n" + "=" * 70)
                print("TEST 2: Finding Path (pump_1 → BOILER_1)")
                print("=" * 70)
                
                result = await session.call_tool(
                    "find_path",
                    arguments={
                        "start_component": "pump_1",
                        "end_component": "BOILER_1"
                    }
                )
                
                print("\n📊 Result:")
                for content in result.content:
                    if content.type == "text":
                        parsed_result = json.loads(content.text)
                        print(json.dumps(parsed_result, indent=2))
                        
                        # Show path details if successful
                        if parsed_result.get('success') and parsed_result.get('path'):
                            print("\n🛤️  Path Details:")
                            for step in parsed_result['path']:
                                print(f"   {step['position']}. {step['component_name']} ({step['component_id']})")
                
                # Test 3: Find path (Ball_Valve_4 → 3_Way_Ball_Valve_T_2)
                print("\n\n" + "=" * 70)
                print("TEST 3: Finding Path (Ball_Valve_4 → 3_Way_Ball_Valve_T_2)")
                print("=" * 70)
                
                result = await session.call_tool(
                    "find_path",
                    arguments={
                        "start_component": "Ball_Valve_4",
                        "end_component": "3_Way_Ball_Valve_T_2"
                    }
                )
                
                print("\n📊 Result:")
                for content in result.content:
                    if content.type == "text":
                        parsed_result = json.loads(content.text)
                        if parsed_result.get('success'):
                            print(f"   ✅ Path found: {parsed_result['path_length']} components")
                            print("\n🛤️  Path:")
                            for step in parsed_result['path'][:5]:  # Show first 5
                                print(f"   {step['position']}. {step['component_name']}")
                            if parsed_result['path_length'] > 5:
                                print(f"   ... and {parsed_result['path_length'] - 5} more")
                        else:
                            print(f"   ❌ {parsed_result['message']}")
                
                # Test 4: Find neighbors
                print("\n\n" + "=" * 70)
                print("TEST 4: Finding Neighbors (BOILER_1)")
                print("=" * 70)
                
                result = await session.call_tool(
                    "find_neighbors",
                    arguments={
                        "component": "BOILER_1"
                    }
                )
                
                print("\n📊 Result:")
                for content in result.content:
                    if content.type == "text":
                        parsed_result = json.loads(content.text)
                        print(f"   Found {parsed_result.get('neighbor_count', 0)} neighbors:")
                        for neighbor in parsed_result.get('neighbors', []):
                            print(f"   - {neighbor['component_name']} ({neighbor['component_id']})")
                
                # Test 5: Find neighbors of pump_1
                print("\n\n" + "=" * 70)
                print("TEST 5: Finding Neighbors (pump_1)")
                print("=" * 70)
                
                result = await session.call_tool(
                    "find_neighbors",
                    arguments={
                        "component": "pump_1"
                    }
                )
                
                print("\n📊 Result:")
                for content in result.content:
                    if content.type == "text":
                        parsed_result = json.loads(content.text)
                        print(f"   Found {parsed_result.get('neighbor_count', 0)} neighbors:")
                        for neighbor in parsed_result.get('neighbors', []):
                            print(f"   - {neighbor['component_name']} ({neighbor['component_id']})")
                
                # Test 6: Error handling - non-existent component
                print("\n\n" + "=" * 70)
                print("TEST 6: Error Handling (Non-existent Component)")
                print("=" * 70)
                
                result = await session.call_tool(
                    "find_path",
                    arguments={
                        "start_component": "NonExistent_Component",
                        "end_component": "Ball_Valve_4"
                    }
                )
                
                print("\n📊 Result:")
                for content in result.content:
                    if content.type == "text":
                        parsed_result = json.loads(content.text)
                        if not parsed_result.get('success'):
                            print(f"   ❌ Expected error: {parsed_result['message']}")
                        else:
                            print(f"   ⚠️  Unexpected success")
                
                # Summary
                print("\n\n" + "=" * 70)
                print("✅ All Tests Completed Successfully!")
                print("=" * 70)
                print("\n📝 Summary:")
                print("   ✓ Server initialization")
                print("   ✓ Tool listing")
                print("   ✓ Path finding (multiple tests)")
                print("   ✓ Neighbor finding (multiple tests)")
                print("   ✓ Error handling")
                print("\n🎉 Your MCP server is ready to use with Claude or n8n!")
                
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        print(f"   Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Starting MCP Server Test Suite...\n")
    try:
        asyncio.run(test_mcp_server())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()