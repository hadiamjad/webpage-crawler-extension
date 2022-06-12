import matplotlib.pyplot as plt
import os
import networkx as nx
import numpy as np
import pandas as pd
import json
from graphviz import Digraph

# from stellargraph.data import BiasedRandomWalk
# from stellargraph import StellarGraph
# from stellargraph import datasets
# from IPython.display import display, HTML
from populateGraph import addNode, addEdge

print('-----------------Import----------------')

# node labels
label = [0]

def createWebGraph(url):
    
    # name: [id, type, TC, FC, label]
    nodes = {}
    # src@tar = [src_id, tar_id, type]
    edges = {}
    # script_dic = {'https://ad/test.js': [set->[_gid,..], get->[_svd, ..]]}
    script_dic = {} 
    # storage_dic = {'_gid' = [002, 5288992, 1], '_svd' = [5]}
    storage_dic = {}

    # initial HTML iframe
    src = addNode(nodes, "Network@https://"+url+"/", "Network", 0 , 0, -1)
    tar = addNode(nodes, "HTML@https://"+url+"/", "HTML@iframe", 0 , 0, -2)
    addEdge(edges, src, tar, 'Network->HTML/Script')
    src = addNode(nodes, "Script@https://"+url+"/", "Script", 0 , 0, 0)
    addEdge(edges, tar, src, 'Initiated')

    # creating storage nodes and edges
    with open(r'server/cookie_storage.json') as file:
      for line in file:
        dataset = json.loads(line)
        if url in dataset["top_level_url"]:
          addStorage(script_dic, storage_dic, dataset) 
    for key in storage_dic:
      addNode(nodes, "Storage@"+key, "Storage", 0 , 0, -3)

    # reading big request data line by line
    with open(r'labellings.json') as file:
      for line in file:
        data = json.loads(line)
        for dataset in data:
          ######### Single request level graph plotting #########
          # check to ensure graph is for one page
          if dataset['top_level_url'] == url:
            # create network node
            src = addNode(nodes, "Network@"+dataset["http_req"], "Network", 0 , 0, -1)
            
            # check if request is redirected
            rdurl = getRedirection(dataset["request_id"], dataset["http_req"])
            if rdurl is not None:
              tar = addNode(nodes, "Network@"+rdurl, "Network", 0 , 0, -1)
              addEdge(edges, src, tar, 'Redirection')
            
            # if request setting up any cookie
            lst = getReqCookie(dataset["request_id"])
            for item in lst:
              lst1 = item.split(";")
              for item1 in lst1:
                # update the storage dictionary
                keys = getStorageDic(storage_dic, item1.split("=")[0])
                tar = addNode(nodes, "Storage@"+keys, "Storage", 0 , 0, -3)
                storage_dic[keys].append(item1.split("=")[1])
                # add html and storage node
                addEdge(edges, src, tar, 'Storage Setter')
            
            # check if resource type is not script then create simple HTML node
            if dataset["resource_type"] != "Script":
              tar = addNode(nodes, "HTML@"+dataset["http_req"], "HTML@"+dataset["resource_type"], 0, 0, -2)
            # create script node
            else:
              if dataset['easylistflag'] == 1 or dataset['easyprivacylistflag'] == 1 or dataset['ancestorflag'] == 1:
                tar = addNode(nodes, "Script@"+dataset["http_req"], dataset["resource_type"], 0, 0, 1)
              else:
                tar = addNode(nodes, "Script@"+dataset["http_req"], dataset["resource_type"], 0, 0, 0)
            # create edge between the Request -> HTML/Script
            addEdge(edges, src, tar, 'Network->HTML/Script')
            
            # if its initiated by call stack javascript
            # else its generated from main iframe
            if dataset['call_stack']['type'] == 'script':
              if dataset['easylistflag'] == 1 or dataset['easyprivacylistflag'] == 1 or dataset['ancestorflag'] == 1:
                tar = addNode(nodes, "Script@"+getInitiator(dataset['call_stack']['stack']), "Script", 1, 0, 0)
              else:
                tar = addNode(nodes, "Script@"+getInitiator(dataset['call_stack']['stack']), "Script", 0, 1, 0)
              addEdge(edges, tar, src, 'Initiated')
            else:
              addEdge(edges, nodes["HTML@https://www."+url+"/"][0], src, 'Initiated')
            
            # Links between storage nodes and script [setter, getter]
            if dataset["http_req"] in script_dic.keys():
              # script -> setter 
              if len(script_dic[dataset["http_req"]][0]) != 0:
                 for item in script_dic[dataset["http_req"]][0]:
                   addEdge(edges, nodes['Script@'+dataset["http_req"]][0], nodes['Storage@'+item][0], 'Storage Setter')
              # getter -> script
              if len(script_dic[dataset["http_req"]][1]) != 0:
                 for item in script_dic[dataset["http_req"]][1]:
                   addEdge(edges, nodes['Storage@'+item][0], nodes['Script@'+dataset["http_req"]][0], 'Storage Getter')

            # if url has storage info 
            val = IsInfoShared(storage_dic, dataset["http_req"])
            if val is not None:
              addEdge(edges, nodes['Storage@'+val][0], src, 'Info Shared')
    
    print(nodes)
    print(edges)

    plot = Digraph(comment='The Round Table')

    for key in nodes:
      
      if nodes[key][1] == 'Script':
        if nodes[key][4] == 1:
          plot.node(str(nodes[key][0]), str(nodes[key][0]), color='red', style='filled')
        elif nodes[key][2] == 0:
          plot.node(str(nodes[key][0]), str(nodes[key][0]), color='green', style='filled')
        elif nodes[key][3] == 0 and nodes[key][2] != 0:
          plot.node(str(nodes[key][0]), str(nodes[key][0]), color='red', style='filled')
        else:
          plot.node(str(nodes[key][0]), str(nodes[key][0]), color='yellow', style='filled')
      elif nodes[key][4] == -3:
        plot.node(str(nodes[key][0]), str(nodes[key][0]), color='blue', style='filled')
      elif nodes[key][4] == -2:
        plot.node(str(nodes[key][0]),str(nodes[key][0]), color='orange', style='filled')
      else:
        plot.node(str(nodes[key][0]), str(nodes[key][0]), color='purple', style='filled')
    
    for key in edges:
      if edges[key][2] == 'Network->HTML/Script':
        plot.edge(str(edges[key][0]), str(edges[key][1]), arrowhead='normal')
      elif edges[key][2] == 'Info Shared':
        plot.edge(str(edges[key][0]), str(edges[key][1]), arrowhead='diamond')
      elif edges[key][2] == 'Initiated':
        plot.edge(str(edges[key][0]), str(edges[key][1]), arrowhead='tee')
      elif edges[key][2] == 'Redirection':
        plot.edge(str(edges[key][0]), str(edges[key][1]), arrowhead='halfopen')
      elif edges[key][2] == 'Storage Getter':
        plot.edge(str(edges[key][0]), str(edges[key][1]), arrowhead='crow')
      else:
        plot.edge(str(edges[key][0]), str(edges[key][1]), arrowhead='crow')
    
    plot.render('test-output/cmovies.online.json.gv', view=True)


def main2():
  createWebGraph('cmovies.online')


# main2()