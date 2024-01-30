from typing import List

from hummingbot.smart_components.strategy_frameworks.data_types import (
    BotAction,
    CreateDCAExecutorAction,
    CreatePositionExecutorAction,
    ExecutorHandlerReport,
    StopDCAExecutorAction,
    StopExecutorAction,
    StoreDCAExecutorAction,
    StoreExecutorAction,
)
from hummingbot.smart_components.strategy_frameworks.executor_handler_base import ExecutorHandlerBase
from hummingbot.smart_components.strategy_frameworks.generic_strategy.generic_controller import GenericController
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase


class GenericExecutor(ExecutorHandlerBase):
    """
    Generic executor handler for a strategy.
    """

    def on_stop(self):
        """Actions to perform on stop."""
        for executor in self.position_executors.values():
            executor.early_stop()
        self.controller.stop()

    def __init__(self, strategy: ScriptStrategyBase, controller: GenericController, update_interval: float = 1.0,
                 executors_update_interval: float = 1.0):
        super().__init__(strategy, controller, update_interval, executors_update_interval)
        self.controller = controller

    async def control_task(self):
        """
        Override the control task to implement the dynamic behavior.
        """
        # Collect data for active executors
        executor_handler_report: ExecutorHandlerReport = self.get_executor_handler_report()

        # Determine actions based on the collected data
        self.controller.update_executor_handler_report(executor_handler_report)
        actions = self.controller.determine_actions()

        # Execute actions
        await self.execute_actions(actions)

    def get_executor_handler_report(self):
        """
        Compute information about executors.
        """
        executor_handler_report = ExecutorHandlerReport(
            status=self.status,
            active_position_executors=self.get_active_executors_df(),
            active_position_executors_info=self.active_executors_info(),
            closed_position_executors_info=self.closed_executors_info(),
            dca_executors=self.get_dca_executors_df(),
        )
        return executor_handler_report

    async def execute_actions(self, actions: List[BotAction]):
        """
        Execute the actions and return the status for each action.
        """
        for action in actions:
            if isinstance(action, CreatePositionExecutorAction):
                self.create_position_executor(action.position_config, action.level_id)
            elif isinstance(action, StopExecutorAction):
                self.stop_position_executor(action.executor_id)
            elif isinstance(action, StoreExecutorAction):
                self.store_position_executor(action.executor_id)
            elif isinstance(action, CreateDCAExecutorAction):
                self.create_dca_executor(action.dca_config, action.dca_id)
            elif isinstance(action, StopDCAExecutorAction):
                self.stop_dca_executor(action.dca_id)
            elif isinstance(action, StoreDCAExecutorAction):
                self.store_dca_executor(action.dca_id)
            else:
                raise ValueError(f"Unknown action type {type(action)}")

    def on_start(self):
        if self.controller.is_perpetual:
            self.set_leverage_and_position_mode()

    def set_leverage_and_position_mode(self):
        connector = self.strategy.connectors[self.controller.config.exchange]
        connector.set_position_mode(self.controller.config.position_mode)
        connector.set_leverage(trading_pair=self.controller.config.trading_pair, leverage=self.controller.config.leverage)
