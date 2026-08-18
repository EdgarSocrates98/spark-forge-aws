from sparkforge.agents import AutonomyBudget, AutonomyController

def test_route_selects_minimal_specialist():
    controller = AutonomyController()
    route = controller.route(goal="inspect spark plan", available_agents=["sf-inventory", "sf-judge", "sf-verifier"], completed=set())
    assert route.phase == "inventory"
    assert route.agents == ("sf-inventory",)

def test_route_advances_to_verification_after_analysis():
    controller = AutonomyController()
    route = controller.route(goal="validate finding", available_agents=["sf-judge", "sf-verifier"], completed={"inventory", "collect", "analyze", "judge"})
    assert route.phase == "verify"
    assert route.agents == ("sf-verifier",)

def test_stop_on_stagnation_and_authorization_policy():
    controller = AutonomyController(AutonomyBudget(stagnation_limit=2))
    stop = controller.should_stop(iteration=1, tokens_used=10, progress=0, stagnant_iterations=2)
    assert stop.stop is True
    assert "progress" in stop.reason
    assert controller.authorize_tool(agent="a", tool="write", allowed_tools=["write"], mutating=True)[0] is False
    assert controller.authorize_tool(agent="a", tool="write", allowed_tools=["write"], mutating=True, approval=True)[0] is True
