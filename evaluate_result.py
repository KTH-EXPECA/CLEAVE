#  Copyright (c) 2020 KTH Royal Institute of Technology
#
#  Licensed under the Apache License, Version 2.0 (the 'License');
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an 'AS IS' BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#   limitations under the License.

import os
import csv
import matplotlib.pyplot as plt
import pylab
import numpy as np

def plot_values(values,x_label,title,percent,type):
    values=np.sort(values)
    plt.figure()
    plt.scatter(values,np.arange(0,1,1/len(values)), marker=".")
    if type=="time":
        plt.hlines(percent,min(values),max(values), colors="r",linestyles= 'dotted')
        plt.text(min(values),percent,str(int(100*percent))+"%")
        x=values[int(percent*len(values))]
        print('' +str(percent*100) + "% of the RTT is less than: "+ str(float("{:.5f}".format(x)))+" (sec)" )
        plt.vlines(x, 0,1,color="r",linestyles ="dashed" ) #linestyles : {'solid', 'dashed', 'dashdot', 'dotted'},
        plt.text(x,0,str(float("{:.5f}".format(x))))

    elif type=="angle":
        bottom_percent=(1-percent)/2
        up_percent=1-bottom_percent
        plt.hlines(up_percent,min(values),max(values), colors="r",linestyles= 'dotted')
        plt.text(min(values),up_percent,str(int(100*up_percent))+"%")
        plt.hlines(bottom_percent,min(values),max(values), colors="r",linestyles= 'dotted')
        plt.text(min(values),bottom_percent,str(int(100*bottom_percent))+"%")

        x_left=values[int(bottom_percent*len(values))]
        x_right=values[int(up_percent*len(values))]
        print('' +str(percent*100) + "% of the data is between ["+ str(float("{:.5f}".format(x_left)))+", "+str(float("{:.5f}".format(x_right)))+"] (rad)" )
        plt.vlines(x_left, 0,1,color="r",linestyles ="dashed" ) #linestyles : {'solid', 'dashed', 'dashdot', 'dotted'},
        plt.vlines(x_right, 0,1,color="r",linestyles ="dashed" )
        plt.text(x_left,0.6,str(float("{:.5f}".format(x_left))))
        plt.text(x_right,0.4,str(float("{:.5f}".format(x_right))))


    plt.grid(linewidth=0.2)
    plt.xlabel(x_label)
    plt.ylabel("Cumulative distribution")
    plt.title(title+" ")

def extract(file_name, col,folder,sample_rate=1):
    with open(folder+file_name, newline='') as csvfile:
        simulation=csv.reader(csvfile)
        output=list()
        for row in simulation:
            try:  # bypass the first irrelevant rows. (text)
                output.append(float(row[col]))
            except:
                continue
        return output

def main():
    print("\n Evaluating the results ---------->\n")

    # extract output angle and rtt from plant metrics
    files=os.listdir("plant_metrics")
    try:
        for i in files:
            if "si" == i[0:2]:
                sim_csv= i
                f = open("plant_metrics/"+sim_csv, "r")
                first_row=f.readline().strip("\n").split(",")
                index_angle= first_row.index("output_angle")
                #print("first line : output angle ",first_row, index_angle)
            elif "ud" == i[0:2]:
                udp_csv= i
                f = open("plant_metrics/"+udp_csv, "r")
                first_row=f.readline().strip("\n").split(",")
                index_rtt= first_row.index("rtt")
                index_seq_plant=first_row.index("seq")
                #print("first line : rtt ",first_row, index_rtt)
        output_ang=extract(sim_csv,index_angle,"plant_metrics/") #  index_angle is the index for output_angle metric in simulation csvfile
        output_rtt=extract(udp_csv,index_rtt,"plant_metrics/") #   index_rtt is the index for RTT metric in udp csvfile
    except:
        print("Looking in the plant metrics folder.")
        print("The files your are looking for might not exist ")
        exit()
    percent=0.98

    plot_values(output_ang,"Angle (rad)", "Inverted pendulum's angle",percent,type="angle")
    plot_values(output_rtt, "Time (s)", "The closed-loop control system RTT",percent,type="time")

    # calculate packet loss
    files=os.listdir("controller_metrics")
    try:
        for i in files:
                if "se" == i[0:2]:
                    service_csv= i
                    f = open("controller_metrics/"+service_csv, "r")
                    first_row=f.readline().strip("\n").split(",")
                    index_seq_controller= first_row.index("seq")
                    #print("first line : seq index ",first_row, index_seq_controller)
        seq_plant = int(extract(udp_csv,index_seq_plant,"plant_metrics/")[-1])
        seq_controller = int(extract(service_csv,index_seq_controller,"controller_metrics/")[-1])
    except:
        print("Looking in the control metrics folder.")
        print("The files your are looking for might not exist")
        exit()

    print("Packet loss: "+" %", (abs(seq_plant-seq_controller)/seq_plant )*100 )
    plt.show()
    remove=input("Do you want to delete the csv files from plant and controller? y/n     ")

    if remove =="y":
        for i in files:
            os.remove("plant_metrics/"+i)
        os.remove("control_metrics/"+service_csv)
main()
