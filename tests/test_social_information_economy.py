from sim.economy import EconomySystem, Firm
from sim.information import InformationSystem, Message
from sim.social import SocialGraph


def test_social_graph_integrity():
    g = SocialGraph()
    g.add_edge('a1', 'a2', 'friendship', trust=0.9)
    g.add_edge('a2', 'a3', 'coworker', trust=0.6)
    assert g.degree('a2') == 1
    assert 'a2' in g.neighbors('a1')


def test_information_propagation():
    g = SocialGraph()
    g.add_edge('a1', 'a2', 'friendship')
    g.add_edge('a2', 'a3', 'friendship')
    inf = InformationSystem(seed=1)
    msg = Message('m1', 'a1', 'news', reliability=0.8, confidence=0.7, mutation_probability=0.5)
    inbox = inf.propagate(g, ['a1'], msg)
    assert 'a2' in inbox
    assert 'a3' in inbox


def test_economic_transactions_and_market_tick():
    eco = EconomySystem()
    eco.add_firm(Firm(firm_id='f1', city_id='c1', sector='food', wage_offer=1.2, productivity=0.8))
    eco.add_firm(Firm(firm_id='f2', city_id='c1', sector='tools', wage_offer=1.0, productivity=1.1))
    eco.market_tick()
    assert eco.city_profiles['c1'].wage_index > 0
    remaining, spent = eco.execute_transaction(1.0, 0.25)
    assert remaining == 0.75
    assert spent == 0.25
