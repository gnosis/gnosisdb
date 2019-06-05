# -*- coding: utf-8 -*-
from decimal import Decimal
from time import mktime

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from django_eth_events.utils import normalize_address_without_0x

from ipfs.ipfs import Ipfs
from tradingdb.relationaldb.models import (BuyOrder, CategoricalEvent,
                                           CentralizedOracle, Event, Market,
                                           OutcomeToken, OutcomeTokenBalance,
                                           ScalarEvent, SellOrder,
                                           TournamentParticipant,
                                           TournamentParticipantBalance)
from tradingdb.relationaldb.tests.factories import (CategoricalEventFactory,
                                                    CentralizedOracleFactory,
                                                    MarketFactory,
                                                    OracleFactory,
                                                    OutcomeTokenFactory,
                                                    ScalarEventFactory,
                                                    TournamentParticipantBalanceFactory,
                                                    generate_eth_account,
                                                    generate_transaction_hash)

from ..event_receivers import (CentralizedOracleFactoryReceiver,
                               CentralizedOracleInstanceReceiver,
                               EventFactoryReceiver, EventInstanceReceiver,
                               GenericIdentityManagerReceiver,
                               MarketFactoryReceiver, MarketInstanceReceiver,
                               OutcomeTokenInstanceReceiver,
                               TournamentTokenReceiver,
                               UportIdentityManagerReceiver)


class TestEventReceiver(TestCase):

    def setUp(self):
        self.ipfs_api = Ipfs()

    def to_timestamp(self, datetime_instance):
        return mktime(datetime_instance.timetuple())

    def test_centralized_oracle_receiver(self):
        oracle1 = CentralizedOracleFactory()
        # saving event_description to IPFS
        event_description_json = {
            'title': oracle1.event_description.title,
            'description': oracle1.event_description.description,
            'resolutionDate': oracle1.event_description.resolution_date.isoformat(),
            'outcomes': oracle1.event_description.outcomes
        }

        ipfs_hash = self.ipfs_api.post(event_description_json)

        block = {
            'number': oracle1.creation_block,
            'timestamp': self.to_timestamp(oracle1.creation_date_time)
        }

        oracle_event = {
            'name': 'CentralizedOracleCreation',
            'address': oracle1.factory,
            'params': [
                {
                    'name': 'creator',
                    'value': oracle1.creator
                },
                {
                    'name': 'centralizedOracle',
                    'value': oracle1.address,
                },
                {
                    'name': 'ipfsHash',
                    'value': ipfs_hash
                }
            ]
        }
        # Delete oracle instance from database
        oracle1.delete()
        # Run the event receiver, it should save data back to database
        CentralizedOracleFactoryReceiver().save(oracle_event, block)
        saved_oracle1 = CentralizedOracle.objects.get(address=oracle1.address)
        self.assertIsNotNone(saved_oracle1.pk)

        # delete saved oracle1
        saved_oracle1.delete()

        # Update oracle creation event data, set new creator address and new ipfs_hash
        new_oracle_creator_address = generate_eth_account(only_address=True)
        oracle_event.get('params')[0].update({'value': new_oracle_creator_address})
        oracle_event.get('params')[2].update({'value': saved_oracle1.event_description.ipfs_hash})

        # Run the event receiver, it should save data back to database
        instance = CentralizedOracleFactoryReceiver().save(oracle_event, block)
        self.assertIsNotNone(instance)

        saved_oracle2 = CentralizedOracle.objects.get(creator=new_oracle_creator_address)
        self.assertEqual(saved_oracle1.address, saved_oracle2.address)

    def test_scalar_event_receiver(self):
        oracle = OracleFactory()
        event = ScalarEventFactory()
        event_address = event.address

        block = {
            'number': oracle.creation_block,
            'timestamp': self.to_timestamp(oracle.creation_date_time)
        }

        scalar_event = {
            'address': event.factory,
            'name': 'ScalarEventCreation',
            'params': [
                {
                    'name': 'creator',
                    'value': event.creator
                },
                {
                    'name': 'collateralToken',
                    'value': event.collateral_token
                },
                {
                    'name': 'oracle',
                    'value': oracle.address
                },
                {
                    'name': 'outcomeCount',
                    'value': 2
                },
                {
                    'name': 'upperBound',
                    'value': event.upper_bound
                },
                {
                    'name': 'lowerBound',
                    'value': event.lower_bound
                },
                {
                    'name': 'scalarEvent',
                    'value': event_address
                }
            ]
        }
        event.delete()
        EventFactoryReceiver().save(scalar_event, block)
        event = ScalarEvent.objects.get(address=event_address)
        self.assertIsNotNone(event.pk)

    def test_categorical_event_receiver(self):
        event = CategoricalEventFactory()
        oracle = OracleFactory()
        event_address = event.address

        block = {
            'number': event.creation_block,
            'timestamp': self.to_timestamp(event.creation_date_time)
        }

        categorical_event = {
            'address': event.factory,
            'name': 'CategoricalEventCreation',
            'params': [
                {
                    'name': 'creator',
                    'value': event.creator
                },
                {
                    'name': 'collateralToken',
                    'value': event.collateral_token
                },
                {
                    'name': 'oracle',
                    'value': oracle.address
                },
                {
                    'name': 'outcomeCount',
                    'value': 2
                },
                {
                    'name': 'categoricalEvent',
                    'value': event_address
                }
            ]
        }
        event.delete()

        EventFactoryReceiver().save(categorical_event, block)
        event = CategoricalEvent.objects.get(address=event_address)
        self.assertIsNotNone(event.pk)

    def test_market_receiver(self):
        oracle = CentralizedOracleFactory()
        oracle.event_description.outcomes = ['1', '2', '3']
        oracle.event_description.save()
        event = CategoricalEventFactory(oracle=oracle)
        market = MarketFactory()
        event_address = event.address

        block = {
            'number': market.creation_block,
            'timestamp': self.to_timestamp(market.creation_date_time)
        }

        market_dict = {
            'name': 'StandardMarketCreation',
            'address': market.factory,
            'params': [
                {
                    'name': 'creator',
                    'value': market.creator
                },
                {
                    'name': 'centralizedOracle',
                    'value': oracle.address,
                },
                {
                    'name': 'marketMaker',
                    'value': market.market_maker
                },
                {
                    'name': 'fee',
                    'value': market.fee
                },
                {
                    'name': 'eventContract',
                    'value': event_address
                },
                {
                    'name': 'fee',
                    'value': market.fee
                },
                {
                    'name': 'market',
                    'value': market.address
                }
            ]
        }

        market.delete()

        MarketFactoryReceiver().save(market_dict, block)
        with self.assertRaises(Market.DoesNotExist):
            Market.objects.get(event=event_address)

        market_dict.get('params')[2].update({'value': normalize_address_without_0x(settings.LMSR_MARKET_MAKER)})
        MarketFactoryReceiver().save(market_dict, block)
        saved_market = Market.objects.get(event=event_address)
        self.assertIsNotNone(saved_market.pk)
        self.assertEqual(len(market.net_outcome_tokens_sold), 2)
        self.assertEqual(len(saved_market.net_outcome_tokens_sold), 3)

    #
    # contract instances
    #
    def test_event_instance_receiver(self):
        outcome_token = OutcomeTokenFactory()
        oracle = OracleFactory()
        event = ScalarEventFactory()
        event_address = event.address

        block = {
            'number': event.creation_block,
            'timestamp': mktime(event.creation_date_time.timetuple())
        }

        scalar_event = {
            'name': 'ScalarEventCreation',
            'address': event.factory,
            'params': [
                {
                    'name': 'creator',
                    'value': event.creator
                },
                {
                    'name': 'collateralToken',
                    'value': event.collateral_token
                },
                {
                    'name': 'oracle',
                    'value': oracle.address
                },
                {
                    'name': 'outcomeCount',
                    'value': 2
                },
                {
                    'name': 'upperBound',
                    'value': event.upper_bound
                },
                {
                    'name': 'lowerBound',
                    'value': event.lower_bound
                },
                {
                    'name': 'scalarEvent',
                    'value': event_address
                }
            ]
        }
        event.delete()

        EventFactoryReceiver().save(scalar_event, block)
        event = ScalarEvent.objects.get(address=event_address)

        block = {
            'number': event.creation_block,
            'timestamp': mktime(event.creation_date_time.timetuple())
        }
        outcome_token_address = outcome_token.address
        outcome_event = {
            'name': 'OutcomeTokenCreation',
            'address': event_address,
            'params': [
                {
                    'name': 'outcomeToken',
                    'value': outcome_token_address,
                },
                {
                    'name': 'index',
                    'value': outcome_token.index
                }
            ]
        }
        outcome_token.delete()
        EventInstanceReceiver().save(outcome_event, block)
        self.assertIsNotNone(OutcomeToken.objects.get(address=outcome_token_address))

    def test_event_instance_issuance_receiver(self):
        outcome_token = OutcomeTokenFactory()
        event = {
            'name': 'Issuance',
            'address': outcome_token.address,
            'params': [
                {
                    'name': 'owner',
                    'value': outcome_token.event.creator
                },
                {
                    'name': 'amount',
                    'value': 1000,
                }
            ]
        }

        OutcomeTokenInstanceReceiver().save(event)
        outcome_token_saved = OutcomeToken.objects.get(address=outcome_token.address)
        self.assertIsNotNone(outcome_token_saved.pk)
        self.assertEqual(outcome_token.total_supply + 1000, outcome_token_saved.total_supply)
        outcome_token_balance = OutcomeTokenBalance.objects.get(owner=outcome_token.event.creator)
        self.assertIsNotNone(outcome_token_balance.pk)
        self.assertEqual(outcome_token_balance.balance, 1000)

    def test_event_instance_revocation_receiver(self):
        outcome_token = OutcomeTokenFactory()
        revocation_event = {
            'name': 'Revocation',
            'address': outcome_token.address,
            'params': [
                {
                    'name': 'owner',
                    'value': outcome_token.event.creator
                },
                {
                    'name': 'amount',
                    'value': 1000,
                }
            ]
        }

        issuance_event = revocation_event.copy()
        issuance_event.update({'name': 'Issuance'})

        # do issuance
        OutcomeTokenInstanceReceiver().save(issuance_event)
        # do revocation
        OutcomeTokenInstanceReceiver().save(revocation_event)
        outcome_token_saved = OutcomeToken.objects.get(address= outcome_token.address)
        self.assertIsNotNone(outcome_token_saved.pk)
        self.assertEqual(outcome_token.total_supply, outcome_token_saved.total_supply)

    def test_event_instance_outcome_assignment_receiver(self):
        event = CategoricalEventFactory()
        assignment_event = {
            'name': 'OutcomeAssignment',
            'address': event.address,
            'params': [{
                'name': 'outcome',
                'value': 1,
            }]
        }

        EventInstanceReceiver().save(assignment_event)
        saved_event = Event.objects.get(address=event.address)
        self.assertTrue(saved_event.is_winning_outcome_set)

    def test_event_instance_winnings_redemption_receiver(self):
        event = CategoricalEventFactory()
        redemption_event = {
            'name': 'WinningsRedemption',
            'address': event.address,
            'params': [
                {
                    'name': 'receiver',
                    'value': event.creator,
                },
                {
                    'name': 'winnings',
                    'value': 1
                }
            ]
        }

        EventInstanceReceiver().save(redemption_event)
        saved_event = Event.objects.get(address=event.address)
        self.assertEqual(saved_event.redeemed_winnings, event.redeemed_winnings + 1)

    def test_centralized_oracle_instance_owner_replacement_receiver(self):
        oracle0 = CentralizedOracleFactory()
        oracle1 = CentralizedOracleFactory()
        new_owner = oracle1.address
        change_owner_event = {
            'name': 'OwnerReplacement',
            'address': oracle0.address,
            'params': [
                {
                    'name': 'newOwner',
                    'value': new_owner
                }
            ]
        }

        CentralizedOracleInstanceReceiver().save(change_owner_event)
        saved_oracle = CentralizedOracle.objects.get(address=oracle0.address)
        self.assertEqual(saved_oracle.owner, new_owner)

    def test_centralized_oracle_instance_outcome_assignment_receiver(self):
        oracle = CentralizedOracleFactory()
        assignment_event = {
            'name': 'OutcomeAssignment',
            'address': oracle.address,
            'params': [{
                'name': 'outcome',
                'value': 1,
            }]
        }

        CentralizedOracleInstanceReceiver().save(assignment_event)
        saved_oracle = CentralizedOracle.objects.get(address=oracle.address)
        self.assertTrue(saved_oracle.is_outcome_set)
        self.assertEqual(saved_oracle.outcome, 1)

    def test_market_funding_receiver(self):
        market = MarketFactory()
        funding_event = {
            'name': 'MarketFunding',
            'address': market.address,
            'params': [
                {
                    'name': 'funding',
                    'value': 100
                }
            ]
        }

        MarketInstanceReceiver().save(funding_event)
        saved_market = Market.objects.get(address=market.address)
        self.assertEqual(saved_market.stage, 1)
        self.assertEqual(saved_market.funding, 100)

    def test_market_closing_receiver(self):
        market = MarketFactory()
        closing_event = {
            'name': 'MarketClosing',
            'address': market.address,
            'params': []
        }

        MarketInstanceReceiver().save(closing_event)
        saved_market = Market.objects.get(address=market.address)
        self.assertEqual(saved_market.stage, 2)

    def test_market_fee_withdrawal_receiver(self):
        market = MarketFactory()
        withdraw_event = {
            'name': 'FeeWithdrawal',
            'address': market.address,
            'params': [
                {
                    'name': 'fees',
                    'value': 10
                }
            ]
        }

        MarketInstanceReceiver().save(withdraw_event)
        saved_market = Market.objects.get(address=market.address)
        # self.assertEqual(market.stage, 3)
        self.assertEqual(saved_market.withdrawn_fees, market.withdrawn_fees+10)

    def test_outcome_token_purchase(self):
        categorical_event = CategoricalEventFactory()
        outcome_token = OutcomeTokenFactory(event=categorical_event, index=0)
        market = MarketFactory(event=categorical_event)
        sender_address = generate_eth_account(only_address=True)

        outcome_token_purchase_event = {
            'name': 'OutcomeTokenPurchase',
            'address': market.address,
            'transaction_hash': generate_transaction_hash(),
            'params': [
                {'name': 'outcomeTokenCost', 'value': 100},
                {'name': 'marketFees', 'value': 10},
                {'name': 'buyer', 'value': sender_address},
                {'name': 'outcomeTokenIndex', 'value': 0},
                {'name': 'outcomeTokenCount', 'value': 10},
            ]
        }

        block = {
            'number': 1,
            'timestamp': self.to_timestamp(timezone.now())
        }

        self.assertEqual(BuyOrder.objects.all().count(), 0)
        MarketInstanceReceiver().save(outcome_token_purchase_event, block)
        buy_orders = BuyOrder.objects.all()
        self.assertEqual(buy_orders.count(), 1)
        self.assertEqual(buy_orders[0].cost, 110) # outcomeTokenCost+fee
        self.assertEqual(buy_orders[0].transaction_hash, outcome_token_purchase_event['transaction_hash'])

    def test_outcome_token_purchase_marginal_price(self):
        categorical_event = CategoricalEventFactory()
        OutcomeTokenFactory(event=categorical_event, index=0)
        OutcomeTokenFactory(event=categorical_event, index=1)
        market = MarketFactory(event=categorical_event, funding=1e18, net_outcome_tokens_sold=[0, 0])
        sender_address = generate_eth_account(only_address=True)

        outcome_token_purchase_event = {
            'name': 'OutcomeTokenPurchase',
            'address': market.address,
            'transaction_hash': generate_transaction_hash(),
            'params': [
                {'name': 'outcomeTokenCost', 'value': 1000000000000000000},
                {'name': 'marketFees', 'value': 0},
                {'name': 'buyer', 'value': sender_address},
                {'name': 'outcomeTokenIndex', 'value': 0},
                {'name': 'outcomeTokenCount', 'value': 1584900000000000000},
            ]
        }

        block = {
            'number': 1,
            'timestamp': self.to_timestamp(timezone.now())
        }

        self.assertEqual(BuyOrder.objects.all().count(), 0)
        MarketInstanceReceiver().save(outcome_token_purchase_event, block)
        buy_orders = BuyOrder.objects.all()
        self.assertEqual(buy_orders.count(), 1)
        self.assertListEqual(buy_orders[0].marginal_prices, [Decimal(0.7500), Decimal(0.2500)])  # outcomeTokenCost+fee
        self.assertEqual(buy_orders[0].transaction_hash, outcome_token_purchase_event['transaction_hash'])

    def test_outcome_token_sell(self):
        categorical_event = CategoricalEventFactory()
        outcome_token = OutcomeTokenFactory(event=categorical_event, index=0)
        market = MarketFactory(event=categorical_event)
        sender_address = generate_eth_account(only_address=True)

        outcome_token_sell_event = {
            'name': 'OutcomeTokenSale',
            'address': market.address,
            'transaction_hash': generate_transaction_hash(),
            'params': [
                {'name': 'outcomeTokenProfit', 'value': 100},
                {'name': 'marketFees', 'value': 10},
                {'name': 'seller', 'value': sender_address},
                {'name': 'outcomeTokenIndex', 'value': 0},
                {'name': 'outcomeTokenCount', 'value': 10},
            ]
        }

        block = {
            'number': 1,
            'timestamp': self.to_timestamp(timezone.now())
        }

        self.assertEqual(SellOrder.objects.all().count(), 0)
        MarketInstanceReceiver().save(outcome_token_sell_event, block)
        sell_orders = SellOrder.objects.all()
        self.assertEqual(sell_orders.count(), 1)
        self.assertEqual(sell_orders[0].profit, 90) # outcomeTokenProfit-fee
        self.assertEqual(sell_orders[0].transaction_hash, outcome_token_sell_event['transaction_hash'])

    def test_collected_fees(self):
        categorical_event = CategoricalEventFactory()
        outcome_token = OutcomeTokenFactory(event=categorical_event, index=0)
        market = MarketFactory(event=categorical_event)
        sender_address = generate_eth_account(only_address=True)
        fees = 10

        outcome_token_purchase_event = {
            'name': 'OutcomeTokenPurchase',
            'address': market.address,
            'transaction_hash': generate_transaction_hash(),
            'params': [
                {'name': 'outcomeTokenCost', 'value': 100},
                {'name': 'marketFees', 'value': fees},
                {'name': 'buyer', 'value': sender_address},
                {'name': 'outcomeTokenIndex', 'value': 0},
                {'name': 'outcomeTokenCount', 'value': 10},
            ]
        }

        block = {
            'number': 1,
            'timestamp': self.to_timestamp(timezone.now())
        }

        # Save event
        MarketInstanceReceiver().save(outcome_token_purchase_event, block)
        # Check that collected fees was incremented
        market_check = Market.objects.get(address=market.address)
        self.assertEqual(market_check.collected_fees, market.collected_fees+fees)
        # Check that the buy order was saved with the correct transaction hash
        buy_order = BuyOrder.objects.get(transaction_hash=outcome_token_purchase_event['transaction_hash'])
        self.assertEqual(buy_order.sender, sender_address)

        block.update({'number': 2})
        MarketInstanceReceiver().save(outcome_token_purchase_event, block)
        market_check = Market.objects.get(address=market.address)
        self.assertEqual(market_check.collected_fees, market.collected_fees+fees+fees)

    def test_create_tournament_participant(self):
        contract_address = "d833215cbcc3f914bd1c9ece3ee7bf8b14f841bb"
        registrant_address = "90f8bf6a479f320ead074411a4b0e7944ea8c9c1"
        registered_mainnet_address = "ffcf8fdee72ac11b5c542428b35eef5769c409f0"
        participant_event = {
            "address": contract_address,
            "name": "AddressRegistration",
            "params": [
                {
                    "name": "registrant",
                    "value": registrant_address,
                },
                {
                    "name": "registeredMainnetAddress",
                    "value": registered_mainnet_address,
                }
            ]
        }

        block = {
            'number': 1,
            'timestamp': self.to_timestamp(timezone.now())
        }

        self.assertEqual(TournamentParticipant.objects.all().count(), 0)
        # Save event
        GenericIdentityManagerReceiver().save(participant_event, block)
        # Check that tournament participants were incremented
        tournament_participant = TournamentParticipant.objects.first()
        self.assertIsNotNone(tournament_participant)
        self.assertEqual(tournament_participant.address, registrant_address)
        self.assertEqual(tournament_participant.mainnet_address, registered_mainnet_address)

    def test_uport_create_tournament_participant(self):
        identity = 'ebe4dd7a4a9e712e742862719aa04709cc6d80a6'
        participant_event = {
            'name': 'IdentityCreated',
            'address': 'abbcd5b340c80b5f1c0545c04c987b87310296ae',
            'params': [
                {
                    'name': 'identity',
                    'value': identity
                },
                {
                    'name': 'creator',
                    'value': '50858f2c7873fac9398ed9c195d185089caa7967'
                },
                {
                    'name': 'owner',
                    'value': '8f357b2c8071c2254afbc65907997f9adea6cc78',
                },
                {
                    'name': 'recoveryKey',
                    'value': 'b67c2d2fcfa3e918e3f9a5218025ebdd12d26212'
                }
            ]
        }

        block = {
            'number': 1,
            'timestamp': self.to_timestamp(timezone.now())
        }

        self.assertEqual(TournamentParticipant.objects.all().count(), 0)
        # Save event
        UportIdentityManagerReceiver().save(participant_event, block)

        tournament_participant = TournamentParticipant.objects.first()
        self.assertIsNotNone(tournament_participant)
        self.assertEqual(tournament_participant.address, identity)

    def test_issue_tournament_tokens(self):
        participant_balance = TournamentParticipantBalanceFactory()
        participant = participant_balance.participant
        amount_to_add = 150
        participant_event = {
            'name': 'Issuance',
            'address': 'not needed',
            'params': [
                {
                    'name': 'owner',
                    'value': participant.address
                },
                {
                    'name': 'amount',
                    'value': amount_to_add
                }
            ]
        }

        self.assertEqual(TournamentParticipantBalance.objects.get(participant=participant.address).balance,
                         participant_balance.balance)
        # Save event
        TournamentTokenReceiver().save(participant_event)
        self.assertEqual(TournamentParticipantBalance.objects.get(participant=participant.address).balance,
                         participant_balance.balance+amount_to_add)

    def test_issue_non_participant(self):
        # should not break, just don't save anything
        participant_balance = TournamentParticipantBalanceFactory()
        participant = participant_balance.participant
        participant_event = {
            'name': 'Issuance',
            'address': 'not needed',
            'params': [
                {
                    'name': 'owner',
                    'value': participant.address
                },
                {
                    'name': 'amount',
                    'value': 123
                }
            ]
        }

        participant.delete()
        # Save event
        TournamentTokenReceiver().save(participant_event)
        self.assertEqual(TournamentParticipant.objects.all().count(), 0)
        self.assertIsNone(participant.pk)

    def test_transfer_tournament_tokens(self):
        participant_balance1 = TournamentParticipantBalanceFactory()
        participant1 = participant_balance1.participant
        participant_balance2 = TournamentParticipantBalanceFactory()
        participant2 = participant_balance2.participant

        participant1_issuance_event = {
            'name': 'Issuance',
            'address': 'not needed',
            'params': [
                {
                    'name': 'owner',
                    'value': participant1.address
                },
                {
                    'name': 'amount',
                    'value': 150
                }
            ]
        }

        transfer_event = {
            'name': 'Transfer',
            'address': 'not needed',
            'params': [
                {
                    'name': 'from',
                    'value': participant1.address
                },
                {
                    'name': 'to',
                    'value': participant2.address
                },
                {
                    'name': 'value',
                    'value': 15
                }
            ]
        }

        # Save event
        TournamentTokenReceiver().save(participant1_issuance_event)
        TournamentTokenReceiver().save(transfer_event)
        self.assertEqual(TournamentParticipantBalance.objects.get(participant=participant1.address).balance.__float__(), float(participant_balance1.balance+150-15))
        self.assertEqual(TournamentParticipantBalance.objects.get(participant=participant2.address).balance.__float__(), float(participant_balance2.balance+15))

    def test_transfer_tournament_tokens_non_to_participants(self):
        participant_balance1 = TournamentParticipantBalanceFactory()
        participant1 = participant_balance1.participant
        participant_balance2 = TournamentParticipantBalanceFactory()
        participant2 = participant_balance2.participant
        participant1_issuance_event = {
            'name': 'Issuance',
            'address': 'not needed',
            'params': [
                {
                    'name': 'owner',
                    'value': participant1.address
                },
                {
                    'name': 'amount',
                    'value': 150
                }
            ]
        }

        transfer_event = {
            'name': 'Transfer',
            'address': 'not needed',
            'params': [
                {
                    'name': 'from',
                    'value': participant1.address
                },
                {
                    'name': 'to',
                    'value': participant2.address
                },
                {
                    'name': 'value',
                    'value': 15
                }
            ]
        }

        participant2.delete()

        # Save event
        TournamentTokenReceiver().save(participant1_issuance_event)
        TournamentTokenReceiver().save(transfer_event)
        self.assertEqual(TournamentParticipantBalance.objects.get(participant=participant1.address).balance.__float__(), float(participant_balance1.balance+150-15))
        self.assertEqual(TournamentParticipant.objects.filter(address=participant2.address).count(), 0)

    def test_transfer_tournament_tokens_non_from_participant(self):
        participant1 = TournamentParticipantBalanceFactory().participant
        participant_balance2 = TournamentParticipantBalanceFactory()
        participant2 = participant_balance2.participant

        transfer_event = {
            'name': 'Transfer',
            'address': 'not needed',
            'params': [
                {
                    'name': 'from',
                    'value': participant1.address
                },
                {
                    'name': 'to',
                    'value': participant2.address
                },
                {
                    'name': 'value',
                    'value': 15
                }
            ]
        }

        participant1.delete()

        # Save event
        TournamentTokenReceiver().save(transfer_event)
        self.assertEqual(TournamentParticipant.objects.filter(address=participant1.address).count(), 0)
        self.assertEqual(TournamentParticipantBalance.objects.get(participant=participant2.address).balance.__float__(), float(participant_balance2.balance+15))
