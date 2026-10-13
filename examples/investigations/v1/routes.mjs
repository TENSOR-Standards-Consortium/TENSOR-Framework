// Explicit authoring decisions. Array order never supplies a graph transition.
// A tuple is [source question number, outcome, target question number].
export const routing = {
  'soc-signin': {
    routes: [[1,'yes',2],[1,'yes',3],[1,'no',7],[1,'unknown',2],[1,'unknown',7],
      [2,'yes',3],[2,'no',3],[2,'unknown',3],[2,'unknown',7],
      [3,'yes',4],[3,'yes',5],[3,'no',7],[3,'unknown',2],[3,'unknown',7],
      [4,'yes',5],[4,'yes',7],[4,'no',5],[4,'no',6],[4,'unknown',5],[4,'unknown',7],
      [5,'yes',7],[5,'no',7],[5,'unknown',7],[6,'yes',7],[6,'no',7],[6,'unknown',7]],
    selected: {1:[2,3],3:[4],4:[5,6],6:[7]},
    context: {4:[3],5:[3],6:[3,4],7:[1,2,3,4,5,6]},
  },
  'workload-cloud-egress': {
    routes: [[1,'yes',2],[1,'yes',3],[1,'no',7],[1,'unknown',2],[1,'unknown',7],
      [2,'yes',4],[2,'no',7],[2,'unknown',4],[2,'unknown',7],
      [3,'yes',5],[3,'no',5],[3,'unknown',5],
      [4,'yes',5],[4,'no',5],[4,'no',6],[4,'unknown',5],[4,'unknown',7],
      [5,'yes',7],[5,'no',7],[5,'unknown',7],[6,'yes',7],[6,'no',7],[6,'unknown',7]],
    selected: {1:[2,3],2:[4],4:[5,6],6:[7]},
    context: {4:[2],5:[2,3],6:[2,3,4],7:[1,2,3,4,5,6]},
  },
  'attachment-host-tool': {
    routes: [[1,'yes',2],[1,'no',9],[1,'unknown',2],[1,'unknown',9],
      [2,'yes',3],[2,'no',9],[2,'unknown',3],[2,'unknown',9],
      [3,'yes',4],[3,'yes',8],[3,'no',9],[3,'unknown',4],[3,'unknown',9],
      [4,'yes',5],[4,'no',9],[4,'unknown',5],[4,'unknown',9],
      [5,'yes',6],[5,'yes',7],[5,'no',7],[5,'unknown',6],[5,'unknown',7],
      [6,'yes',9],[6,'no',9],[6,'unknown',9],[7,'yes',9],[7,'no',9],[7,'unknown',9],
      [8,'yes',9],[8,'no',9],[8,'unknown',9]],
    selected: {1:[2],2:[3],3:[4,8],4:[5],8:[9]}, earlySelected: {5:[6,7]},
    context: {3:[2],4:[3],5:[4],6:[4,5],7:[4,5],8:[3,4,5,6,7],9:[1,2,3,4,5,6,7,8]},
  },
};
