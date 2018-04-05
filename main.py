#!/usr/local/bin/python3

import iroha
import sys

import block_pb2
import endpoint_pb2
import endpoint_pb2_grpc
import queries_pb2
import grpc
import time
import base64
import json

from sys import stdin


query_counter = 1
tx_builder = iroha.ModelTransactionBuilder()
query_builder = iroha.ModelQueryBuilder()
crypto = iroha.ModelCrypto()
proto_tx_helper = iroha.ModelProtoTransaction()
proto_query_helper = iroha.ModelProtoQuery()

admin_priv = open("admin@test.priv", "r").read()
admin_pub = open("admin@test.pub", "r").read()
key_pair = crypto.convertFromExisting(admin_pub, admin_priv)

current_time = int(round(time.time() * 1000)) - 10**5
creator = "admin@test"

max_file_size=4000000



def get_status(tx):
    # Create status request

    print("Hash of the transaction: ", tx.hash().hex())
    tx_hash = tx.hash().blob()

    if sys.version_info[0] == 2:
        tx_hash = ''.join(map(chr, tx_hash))
    else:
        tx_hash = bytes(tx_hash)


    request = endpoint_pb2.TxStatusRequest()
    request.tx_hash = tx_hash

    channel = grpc.insecure_channel('127.0.0.1:50051')
    stub = endpoint_pb2_grpc.CommandServiceStub(channel)

    response = stub.Status(request)
    status = endpoint_pb2.TxStatus.Name(response.tx_status)
    print("Status of transaction is:", status)

    if status != "COMMITTED":
        print("Your transaction wasn't committed")
        exit(1)


def print_status_streaming(tx):
    # Create status request

    print("Hash of the transaction: ", tx.hash().hex())
    tx_hash = tx.hash().blob()

    # Check python version
    if sys.version_info[0] == 2:
        tx_hash = ''.join(map(chr, tx_hash))
    else:
        tx_hash = bytes(tx_hash)

    # Create request
    request = endpoint_pb2.TxStatusRequest()
    request.tx_hash = tx_hash

    # Create connection to Iroha
    channel = grpc.insecure_channel('127.0.0.1:50051')
    stub = endpoint_pb2_grpc.CommandServiceStub(channel)

    # Send request
    response = stub.StatusStream(request)

    for status in response:
        print("Status of transaction:")
        print(status)


def send_tx(tx, key_pair):
    tx_blob = proto_tx_helper.signAndAddSignature(tx, key_pair).blob()
    proto_tx = block_pb2.Transaction()

    if sys.version_info[0] == 2:
        tmp = ''.join(map(chr, tx_blob))
    else:
        tmp = bytes(tx_blob)

    proto_tx.ParseFromString(tmp)

    channel = grpc.insecure_channel('127.0.0.1:50051')
    stub = endpoint_pb2_grpc.CommandServiceStub(channel)

    stub.Torii(proto_tx)


def send_query(query, key_pair):
    query_blob = proto_query_helper.signAndAddSignature(query, key_pair).blob()

    proto_query = queries_pb2.Query()

    if sys.version_info[0] == 2:
        tmp = ''.join(map(chr, query_blob))
    else:
        tmp = bytes(query_blob)

    proto_query.ParseFromString(tmp)

    channel = grpc.insecure_channel('127.0.0.1:50051')
    query_stub = endpoint_pb2_grpc.QueryServiceStub(channel)
    query_response = query_stub.Find(proto_query)

    return query_response


def tx1(filename):
    # chunks = [file_data[i:min(i+max_file_size, len(file_data))] for i in range(0, len(file_data), max_file_size)]
    # print(len(chunks))
    # for i in range(len(chunks)):
    file_data = base64.b64encode(open(filename, "rb").read())
    tx = tx_builder.creatorAccountId(creator) \
        .txCounter(1) \
        .createdTime(current_time) \
        .setAccountDetail(creator, ''.join(hex(ord(x))[2:] for x in filename), file_data.decode()) \
        .build()
    send_tx(tx, key_pair)
    time.sleep(5)
    get_status(tx)



def get_account_detail(read_only=True, file_to_dl=""):
    global query_counter
    query = query_builder.creatorAccountId(creator) \
        .createdTime(current_time) \
        .queryCounter( query_counter) \
        .getAccountDetail(creator) \
        .build()

    query_counter += 1    
    query_response = send_query(query, key_pair)
    detail_info = query_response.account_detail_response.detail

    #print(query_response)
 
    json_data = json.loads(detail_info)
    if read_only:
        for key in json_data[creator].keys():
            print(bytearray.fromhex(key).decode())
    else:
        json_details = json_data[creator][''.join(hex(ord(x))[2:] for x in file_to_dl)]
        decoded_details = base64.b64decode(json_details)
        open(file_to_dl, "wb").write(decoded_details)





while True:
    print("Enter command:")
    command = input()
    if command == "list":
        get_account_detail()
    elif command == "download":
        print("Enter file name:")
        dlfile = input()
        get_account_detail(False, dlfile)
    elif command == "upload":
        print("Enter file name:")
        ufile = input()
        tx1(ufile)
    elif command == "exit":
        exit(0)    
    else:
        print("Unknown command")

