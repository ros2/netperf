# Copyright 2022 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path

import netperf_tool

from ros2netperf.api import add_results_to_csv_output
from ros2netperf.api import add_qos_arguments_to_parser
from ros2netperf.api import get_qos_profile_from_args
from ros2netperf.api import print_results
from ros2netperf.api import print_stats_header
from ros2netperf.api import write_csv_output_to_file
from ros2netperf.verb import VerbExtension


class ServerVerb(VerbExtension):
    """Run server side of ros2 network performance tester."""

    def __init__(self):
        self._next_client_id = 0
        self._gid_id_map = {}
        self._csv_output = []
        self._output_file = None

    def add_arguments(self, parser, cli_name):
        parser.add_argument(
            '-o',
            '--output-file',
            help='CSV output file path.',
            type=Path,
        )
        parser.add_argument(
            '-f',
            '--force',
            help='If the output file exists, it will be overwritten.',
            action='store_true',
        )
        parser.add_argument(
            '-a',
            '--append',
            help='If the output file exists, it will append data to it.',
            action='store_true',
        )
        add_qos_arguments_to_parser(parser)

    def main(self, *, args):
        self._output_file = args.output_file
        mode = 'a'
        if args.output_file is not None and not (args.append and args.output_file.exists()):
            mode = 'w'
            try:
                args.output_file.touch(exist_ok=args.force)
            except FileNotFoundError:
                print(f"Directory '{args.output_file.parent.resolve()}' does not exist")
                return 1
            except FileExistsError:
                print(
                    f"File '{args.output_file.resolve()}' already exists.\n"
                    'Use --force/-f to overwrite.')
                return 1
            self._csv_output.append([
                'Client ID',
                'Duration [s]',
                'Message serialized size',
                'Total MB Received',
                'Bandwidth (measured) [Mbps]',
                'Messages lost',
                'Messages Sent',
                'Lost messages pct',
                'Latency avg ms',
                'Latency min ms',
                'Latency max ms',
                'Latency stdev ms',
            ])
        qos_profile = get_qos_profile_from_args(args)

        runner = netperf_tool.ServerRunner(qos=qos_profile)
        try:
            with runner as node:
                print('---------------------------------------------------------')
                print('Server running')
                print(f'    topic: {node.get_topic_name()}')
                print(f'    qos: {qos_profile}')
                print('---------------------------------------------------------')
                while True:
                    # we wait for 1 second, so we can check for signals in the middle
                    # as the blocking method used by wait_for_results_available()
                    # isn't awaken by signals.
                    self.print_events_from_node(node)
        except KeyboardInterrupt:
            pass
        # if there were more results available, print them
        self.print_events_from_node(node)
        if self._output_file is not None:
            write_csv_output_to_file(self._csv_output, self._output_file, mode)


    def print_events_from_node(self, node):
        node.wait_for_results_available(1.)
        clients_gids = node.extract_new_clients()
        for client_gid in clients_gids:
            self._gid_id_map[client_gid] = self._next_client_id
            print(f'[ {self._next_client_id}] Publisher with gid [{client_gid}] connected')
            self._next_client_id = self._next_client_id + 1
        results_map = node.extract_results()
        self.process_results(results_map)


    def process_results(self, results_map):
        if 0 == len(results_map):
            return
        print_stats_header()
        for gid, results in results_map.items():
            id = self._gid_id_map[gid]
            message_serialized_size = results.collected_info.message_infos[0].serialized_size
            print_results(message_serialized_size, results.statistics, id=id)
            if self._output_file is not None:
                add_results_to_csv_output(message_serialized_size, results.statistics, self._csv_output, id=id)
